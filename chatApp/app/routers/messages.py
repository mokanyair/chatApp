from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user
from app.services.chat_service import ChatService

router = APIRouter()


# =====================================================
# SEND MESSAGE
# POST /messages/
# =====================================================

@router.post("/", response_model=schemas.MessageOut, status_code=201)
def send_message(
    payload: schemas.MessageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return ChatService.send_message(
        db=db,
        sender_id=current_user.id,
        conversation_id=payload.conversation_id,
        content=payload.content
    )


# =====================================================
# GET SINGLE MESSAGE
# GET /messages/{message_id}
# =====================================================

@router.get("/{message_id}", response_model=schemas.MessageOut)
def get_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    message = db.get(models.Message, message_id)

    if not message:
        raise HTTPException(
            status_code=404,
            detail="Message not found"
        )

    participant_ids = {u.id for u in message.conversation.participants}
    if current_user.id not in participant_ids:
        raise HTTPException(
            status_code=403,
            detail="Not a participant in this conversation"
        )

    return message


# =====================================================
# DELETE MESSAGE
# DELETE /messages/{message_id}
# =====================================================

@router.delete("/{message_id}", status_code=204)
def delete_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    ChatService.delete_message(
        db=db,
        message_id=message_id,
        requester_id=current_user.id
    )
