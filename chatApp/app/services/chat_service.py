# app/services/chat_service.py

import structlog
from opentelemetry import trace
from sqlalchemy.orm import Session, joinedload

from fastapi import HTTPException

from app import models
from app.domain_metrics import messages_sent_total, conversations_created_total

log    = structlog.get_logger()
tracer = trace.get_tracer(__name__)


class ChatService:

    # =================================================
    # CREATE OR REUSE DIRECT CONVERSATION
    # =================================================
    @staticmethod
    def get_or_create_direct_conversation(
        db: Session,
        user_a_id: int,
        user_b_id: int
    ):
        if user_a_id == user_b_id:
            raise HTTPException(
                status_code=400,
                detail="Cannot create conversation with yourself"
            )

        user_a = db.get(models.User, user_a_id)
        user_b = db.get(models.User, user_b_id)

        if not user_a or not user_b:
            raise HTTPException(status_code=404, detail="User not found")

        existing = (
            db.query(models.Conversation)
            .filter(models.Conversation.is_group == False)
            .options(joinedload(models.Conversation.participants))
            .all()
        )

        for convo in existing:
            ids = {u.id for u in convo.participants}
            if ids == {user_a_id, user_b_id}:
                return convo

        convo = models.Conversation(
            is_group=False,
            participants=[user_a, user_b]
        )
        db.add(convo)
        db.commit()
        db.refresh(convo)

        conversations_created_total.labels(type="direct").inc()
        log.info("conversation_created", type="direct", conversation_id=convo.id,
                 user_a_id=user_a_id, user_b_id=user_b_id)
        return convo

    # =================================================
    # CREATE GROUP CHAT
    # =================================================
    @staticmethod
    def create_group_conversation(
        db: Session,
        creator_id: int,
        participant_ids: list[int],
        title: str
    ):
        if creator_id not in participant_ids:
            participant_ids.append(creator_id)

        unique_ids = list(set(participant_ids))
        users = (
            db.query(models.User)
            .filter(models.User.id.in_(unique_ids))
            .all()
        )

        if len(users) != len(unique_ids):
            raise HTTPException(status_code=404, detail="One or more users not found")

        convo = models.Conversation(title=title, is_group=True, participants=users)
        db.add(convo)
        db.commit()
        db.refresh(convo)

        conversations_created_total.labels(type="group").inc()
        log.info("conversation_created", type="group", conversation_id=convo.id,
                 creator_id=creator_id, participant_count=len(unique_ids))
        return convo

    # =================================================
    # SEND MESSAGE
    # =================================================
    @staticmethod
    def send_message(
        db: Session,
        sender_id: int,
        conversation_id: int,
        content: str
    ):
        with tracer.start_as_current_span("chat.send_message") as span:
            span.set_attribute("chat.sender_id",       sender_id)
            span.set_attribute("chat.conversation_id", conversation_id)
            span.set_attribute("chat.content_length",  len(content))

            sender       = db.get(models.User,         sender_id)
            conversation = db.get(models.Conversation, conversation_id)

            if not sender:
                raise HTTPException(status_code=404, detail="Sender not found")
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")

            participant_ids = {u.id for u in conversation.participants}
            if sender_id not in participant_ids:
                raise HTTPException(status_code=403, detail="Sender not in conversation")

            message = models.Message(
                content=content.strip(),
                sender_id=sender_id,
                conversation_id=conversation_id,
            )
            db.add(message)
            db.commit()
            db.refresh(message)

            conv_type = "group" if conversation.is_group else "direct"
            messages_sent_total.labels(conversation_type=conv_type).inc()
            span.set_attribute("chat.message_id",       message.id)
            span.set_attribute("chat.conversation_type", conv_type)

            log.info("message_sent", message_id=message.id, sender_id=sender_id,
                     conversation_id=conversation_id, conversation_type=conv_type)
            return message

    # =================================================
    # GET CONVERSATION MESSAGES
    # =================================================
    @staticmethod
    def get_messages(
        db: Session,
        conversation_id: int,
        page: int = 1,
        page_size: int = 20
    ):
        with tracer.start_as_current_span("chat.get_messages") as span:
            span.set_attribute("chat.conversation_id", conversation_id)
            span.set_attribute("pagination.page",      page)
            span.set_attribute("pagination.page_size", page_size)

            if page < 1:
                page = 1
            if page_size > 100:
                page_size = 100

            offset = (page - 1) * page_size
            query = (
                db.query(models.Message)
                .filter(models.Message.conversation_id == conversation_id)
                .order_by(models.Message.created_at.desc())
            )
            total = query.count()
            items = query.offset(offset).limit(page_size).all()

            span.set_attribute("pagination.total", total)
            return {"total": total, "page": page, "page_size": page_size, "items": items}

    # =================================================
    # MARK MESSAGE READ
    # =================================================
    @staticmethod
    def mark_as_read(db: Session, message_id: int):
        message = db.get(models.Message, message_id)
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")

        message.is_read = True
        db.commit()
        db.refresh(message)
        return message

    # =================================================
    # DELETE MESSAGE
    # =================================================
    @staticmethod
    def delete_message(db: Session, message_id: int, requester_id: int):
        with tracer.start_as_current_span("chat.delete_message") as span:
            span.set_attribute("chat.message_id",    message_id)
            span.set_attribute("chat.requester_id",  requester_id)

            message = db.get(models.Message, message_id)
            if not message:
                raise HTTPException(status_code=404, detail="Message not found")

            if message.sender_id != requester_id:
                log.warning("message_delete_forbidden", message_id=message_id,
                            requester_id=requester_id, owner_id=message.sender_id)
                raise HTTPException(status_code=403, detail="Not allowed")

            db.delete(message)
            db.commit()
            log.info("message_deleted", message_id=message_id, requester_id=requester_id)
            return True

    # =================================================
    # ADD USER TO GROUP
    # =================================================
    @staticmethod
    def add_user_to_group(db: Session, conversation_id: int, user_id: int):
        convo = db.get(models.Conversation, conversation_id)
        user  = db.get(models.User,         user_id)

        if not convo or not user:
            raise HTTPException(status_code=404, detail="Conversation or user not found")
        if not convo.is_group:
            raise HTTPException(status_code=400, detail="Not a group conversation")
        if user in convo.participants:
            return convo

        convo.participants.append(user)
        db.commit()
        db.refresh(convo)

        log.info("group_member_added", conversation_id=conversation_id, user_id=user_id)
        return convo

    # =================================================
    # REMOVE USER FROM GROUP
    # =================================================
    @staticmethod
    def remove_user_from_group(db: Session, conversation_id: int, user_id: int):
        convo = db.get(models.Conversation, conversation_id)
        if not convo:
            raise HTTPException(status_code=404, detail="Conversation not found")

        user = db.get(models.User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user in convo.participants:
            convo.participants.remove(user)

        db.commit()
        db.refresh(convo)

        log.info("group_member_removed", conversation_id=conversation_id, user_id=user_id)
        return convo
