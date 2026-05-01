from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas

router = APIRouter()


# =====================================================
# SEND MESSAGE
# POST /messages/
# =====================================================

@router.post("/", status_code=201)
def send_message(
    payload: schemas.MessageCreate,
    db: Session = Depends(get_db)
):
    conversation = db.get(
        models.Conversation,
        payload.conversation_id
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )

    sender = db.get(models.User, 1)   # temp auth placeholder

    message = models.Message(
        content=payload.content,
        sender_id=sender.id,
        conversation_id=conversation.id
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return {
        "message": "Message sent",
        "id": message.id
    }


# =====================================================
# GET SINGLE MESSAGE
# GET /messages/{message_id}
# =====================================================

@router.get("/{message_id}", response_model=schemas.MessageOut)
def get_message(
    message_id: int,
    db: Session = Depends(get_db)
):
    message = db.get(models.Message, message_id)

    if not message:
        raise HTTPException(
            status_code=404,
            detail="Message not found"
        )

    return message


# =====================================================
# DELETE MESSAGE
# DELETE /messages/{message_id}
# =====================================================

@router.delete("/{message_id}")
def delete_message(
    message_id: int,
    db: Session = Depends(get_db)
):
    message = db.get(models.Message, message_id)

    if not message:
        raise HTTPException(
            status_code=404,
            detail="Message not found"
        )

    db.delete(message)
    db.commit()

    return {"detail": "Message deleted"}