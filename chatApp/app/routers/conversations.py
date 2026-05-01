from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user
from app.services.chat_service import ChatService

router = APIRouter()


# =====================================================
# CREATE CONVERSATION
# POST /conversations/
# =====================================================

@router.post("/", response_model=schemas.ConversationOut, status_code=201)
def create_conversation(
    payload: schemas.ConversationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if payload.is_group:
        return ChatService.create_group_conversation(
            db=db,
            creator_id=current_user.id,
            participant_ids=list(payload.participant_ids),
            title=payload.title
        )

    # Direct (1-to-1) conversation: exactly one other participant required
    other_ids = [pid for pid in payload.participant_ids if pid != current_user.id]
    if len(other_ids) != 1:
        raise HTTPException(
            status_code=400,
            detail="Direct conversations require exactly one other participant"
        )

    return ChatService.get_or_create_direct_conversation(
        db=db,
        user_a_id=current_user.id,
        user_b_id=other_ids[0]
    )


# =====================================================
# GET MY CONVERSATIONS
# GET /conversations/
# =====================================================

@router.get("/", response_model=list[schemas.ConversationOut])
def get_conversations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return current_user.conversations


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
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    conversation = db.get(models.Conversation, conversation_id)

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )

    participant_ids = {u.id for u in conversation.participants}
    if current_user.id not in participant_ids:
        raise HTTPException(
            status_code=403,
            detail="Not a participant in this conversation"
        )

    return conversation
