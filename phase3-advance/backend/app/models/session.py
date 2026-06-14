"""Session model - represents a conversation session."""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Session(Base):
    """Conversation session with isolated memory."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), default="default_user", index=True
    )
    title: Mapped[str] = mapped_column(String(255), default="新对话")
    assistant_avatar: Mapped[str] = mapped_column(
        String(500), default="", comment="Custom avatar URL for assistant"
    )
    assistant_nickname: Mapped[str] = mapped_column(
        String(100), default="小石头", comment="Custom nickname for assistant"
    )
    user_avatar: Mapped[str] = mapped_column(
        String(500), default="", comment="Custom avatar URL for user"
    )
    user_nickname: Mapped[str] = mapped_column(
        String(100), default="用户", comment="Custom nickname for user"
    )
    is_global_style: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="Apply style globally to all sessions"
    )
    context_summary: Mapped[str] = mapped_column(
        Text(length=5000), default="", comment="AI-generated summary of the session"
    )
    pending_task: Mapped[str] = mapped_column(
        Text(length=2000), default="", comment="JSON: pending task state for continuity"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    messages = relationship(
        "Message", back_populates="session", cascade="all, delete-orphan"
    )
    files = relationship(
        "FileRecord", back_populates="session", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "assistant_avatar": self.assistant_avatar,
            "assistant_nickname": self.assistant_nickname,
            "user_avatar": self.user_avatar,
            "user_nickname": self.user_nickname,
            "is_global_style": self.is_global_style,
            "context_summary": self.context_summary,
            "pending_task": self.pending_task,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "message_count": len(self.messages) if self.messages else 0,
        }