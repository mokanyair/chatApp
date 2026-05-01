# app/services/chat_service.py

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_

from fastapi import HTTPException, status

from app import models


# =====================================================
# CHAT SERVICE
# =====================================================
# This file contains BUSINESS LOGIC.
#
# Routers should be thin:
#   - receive request
#   - validate schema
#   - call service
#   - return response
#
# Service layer should handle:
#   - database rules
#   - ownership checks
#   - chat workflows
#   - reusable logic
# =====================================================


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
        """
        Creates a 1-to-1 conversation if it does not exist.
        Reuses existing one if already present.
        """

        if user_a_id == user_b_id:
            raise HTTPException(
                status_code=400,
                detail="Cannot create conversation with yourself"
            )

        user_a = db.get(models.User, user_a_id)
        user_b = db.get(models.User, user_b_id)

        if not user_a or not user_b:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        # Search existing direct conversation
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

        # Create new conversation
        convo = models.Conversation(
            is_group=False,
            participants=[user_a, user_b]
        )

        db.add(convo)
        db.commit()
        db.refresh(convo)

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
        """
        Creates a group conversation.
        """

        if creator_id not in participant_ids:
            participant_ids.append(creator_id)

        unique_ids = list(set(participant_ids))

        users = (
            db.query(models.User)
            .filter(models.User.id.in_(unique_ids))
            .all()
        )

        if len(users) != len(unique_ids):
            raise HTTPException(
                status_code=404,
                detail="One or more users not found"
            )

        convo = models.Conversation(
            title=title,
            is_group=True,
            participants=users
        )

        db.add(convo)
        db.commit()
        db.refresh(convo)

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
        """
        Sends message into conversation.
        """

        sender = db.get(models.User, sender_id)
        conversation = db.get(
            models.Conversation,
            conversation_id
        )

        if not sender:
            raise HTTPException(
                status_code=404,
                detail="Sender not found"
            )

        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found"
            )

        # membership check
        participant_ids = {
            user.id for user in conversation.participants
        }

        if sender_id not in participant_ids:
            raise HTTPException(
                status_code=403,
                detail="Sender not in conversation"
            )

        message = models.Message(
            content=content.strip(),
            sender_id=sender_id,
            conversation_id=conversation_id
        )

        db.add(message)
        db.commit()
        db.refresh(message)

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
        """
        Paginated messages.
        """

        if page < 1:
            page = 1

        if page_size > 100:
            page_size = 100

        offset = (page - 1) * page_size

        query = (
            db.query(models.Message)
            .filter(
                models.Message.conversation_id
                == conversation_id
            )
            .order_by(models.Message.created_at.desc())
        )

        total = query.count()

        items = (
            query.offset(offset)
            .limit(page_size)
            .all()
        )

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items
        }

    # =================================================
    # MARK MESSAGE READ
    # =================================================
    @staticmethod
    def mark_as_read(
        db: Session,
        message_id: int
    ):
        """
        Marks message as read.
        """

        message = db.get(models.Message, message_id)

        if not message:
            raise HTTPException(
                status_code=404,
                detail="Message not found"
            )

        message.is_read = True

        db.commit()
        db.refresh(message)

        return message

    # =================================================
    # DELETE MESSAGE
    # =================================================
    @staticmethod
    def delete_message(
        db: Session,
        message_id: int,
        requester_id: int
    ):
        """
        Only sender can delete message.
        """

        message = db.get(models.Message, message_id)

        if not message:
            raise HTTPException(
                status_code=404,
                detail="Message not found"
            )

        if message.sender_id != requester_id:
            raise HTTPException(
                status_code=403,
                detail="Not allowed"
            )

        db.delete(message)
        db.commit()

        return True

    # =================================================
    # ADD USER TO GROUP
    # =================================================
    @staticmethod
    def add_user_to_group(
        db: Session,
        conversation_id: int,
        user_id: int
    ):
        convo = db.get(
            models.Conversation,
            conversation_id
        )

        user = db.get(models.User, user_id)

        if not convo or not user:
            raise HTTPException(
                status_code=404,
                detail="Conversation or user not found"
            )

        if not convo.is_group:
            raise HTTPException(
                status_code=400,
                detail="Not a group conversation"
            )

        if user in convo.participants:
            return convo

        convo.participants.append(user)

        db.commit()
        db.refresh(convo)

        return convo

    # =================================================
    # REMOVE USER FROM GROUP
    # =================================================
    @staticmethod
    def remove_user_from_group(
        db: Session,
        conversation_id: int,
        user_id: int
    ):
        convo = db.get(
            models.Conversation,
            conversation_id
        )

        if not convo:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found"
            )

        user = db.get(models.User, user_id)

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        if user in convo.participants:
            convo.participants.remove(user)

        db.commit()
        db.refresh(convo)

        return convo