from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime
from typing import List, Optional


# =====================================================
# SHARED USER BASE
# =====================================================

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr


# =====================================================
# CREATE USER
# =====================================================

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)


# =====================================================
# USER RESPONSE
# =====================================================

class UserOut(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =====================================================
# LOGIN
# =====================================================

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# =====================================================
# CREATE CONVERSATION
# =====================================================

class ConversationCreate(BaseModel):
    participant_ids: List[int]
    title: Optional[str] = None
    is_group: bool = False


# =====================================================
# MESSAGE CREATE
# =====================================================

class MessageCreate(BaseModel):
    conversation_id: int
    content: str = Field(..., min_length=1, max_length=5000)


# =====================================================
# MESSAGE RESPONSE
# =====================================================

class MessageOut(BaseModel):
    id: int
    content: str
    is_read: bool
    created_at: datetime
    sender: UserOut

    model_config = ConfigDict(from_attributes=True)


# =====================================================
# CONVERSATION RESPONSE
# =====================================================

class ConversationOut(BaseModel):
    id: int
    title: Optional[str]
    is_group: bool
    created_at: datetime

    participants: List[UserOut]
    messages: List[MessageOut] = []

    model_config = ConfigDict(from_attributes=True)


# =====================================================
# MESSAGE LIST (PAGINATION)
# =====================================================

class PaginatedMessages(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[MessageOut]


class AddMemberRequest(BaseModel):
    user_id: int