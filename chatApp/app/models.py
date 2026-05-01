from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Boolean,
    Table,
    Text,
    func
)

from sqlalchemy.orm import relationship
from app.database import Base

# =====================================================
# MANY TO MANY:
# Users <-> Conversations
# =====================================================

conversation_participants = Table(
    "conversation_participants",
    Base.metadata,

    Column(
        "user_id",
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    ),

    Column(
        "conversation_id",
        Integer,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        primary_key=True
    )
)

# =====================================================
# USERS
# =====================================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String(50), unique=True, nullable=False, index=True)

    email = Column(String(255), unique=True, nullable=False, index=True)

    hashed_password = Column(String(255), nullable=False)

    is_active = Column(Boolean, default=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Conversations user belongs to
    conversations = relationship(
        "Conversation",
        secondary=conversation_participants,
        back_populates="participants"
    )

    # Messages user sent
    sent_messages = relationship(
        "Message",
        back_populates="sender"
    )


# =====================================================
# CONVERSATIONS
# =====================================================

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(255), nullable=True)

    is_group = Column(Boolean, default=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    participants = relationship(
        "User",
        secondary=conversation_participants,
        back_populates="conversations"
    )

    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at"
    )


# =====================================================
# MESSAGES
# =====================================================

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)

    content = Column(Text, nullable=False)

    is_read = Column(Boolean, default=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )

    sender_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    conversation_id = Column(
        Integer,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    sender = relationship(
        "User",
        back_populates="sent_messages"
    )

    conversation = relationship(
        "Conversation",
        back_populates="messages"
    )