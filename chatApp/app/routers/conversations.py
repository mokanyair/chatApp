from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas

router = APIRouter()


# =====================================================
# CREATE CONVERSATION
# POST /conversations/
# =====================================================

@router.post("/", response_model=schemas.ConversationOut, status_code=201)
def create_conversation(
    payload: schemas.ConversationCreate,
    db: Session = Depends(get_db)
):
    users = (
        db.query(models.User)
        .filter(models.User.id.in_(payload.participant_ids))
        .all()
    )

    if len(users) != len(payload.participant_ids):
        raise HTTPException(
            status_code=404,
            detail="One or more users not found"
        )

    conversation = models.Conversation(
        title=payload.title,
        is_group=payload.is_group,
        participants=users
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return conversation


# =====================================================
# GET ALL CONVERSATIONS
# GET /conversations/
# =====================================================

@router.get("/", response_model=list[schemas.ConversationOut])
def get_conversations(
    db: Session = Depends(get_db)
):
    return db.query(models.Conversation).all()


# =====================================================
# GET CONVERSATION BY ID
# GET /conversations/{conversation_id}
# =====================================================

@router.get(
    "/{conversation_id}",
    response_model=schemas.ConversationOut
)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    conversation = db.get(
        models.Conversation,
        conversation_id
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )

    return conversation