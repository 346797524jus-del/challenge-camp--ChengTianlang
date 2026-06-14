"""Preference model - stores user preferences and learning patterns."""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Boolean, Integer, Float, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Preference(Base):
    """User preferences that shape assistant behavior and tone."""

    __tablename__ = "preferences"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), default="default_user", index=True)
    session_id: Mapped[str] = mapped_column(
        String(36), default="", comment="Empty means global preference"
    )
    # Tone & style preferences
    tone_style: Mapped[str] = mapped_column(
        String(50), default="friendly",
        comment="friendly, formal, concise, detailed, humorous"
    )
    response_length: Mapped[str] = mapped_column(
        String(20), default="medium",
        comment="short, medium, long"
    )
    language_preference: Mapped[str] = mapped_column(
        String(10), default="zh-CN", comment="Language code"
    )
    # Interface theme
    theme: Mapped[str] = mapped_column(
        String(20), default="light", comment="light, dark, warm"
    )
    # Learning from feedback
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    dislike_count: Mapped[int] = mapped_column(Integer, default=0)
    # Key facts learned about user
    learned_facts: Mapped[str] = mapped_column(
        Text(length=10000), default="", comment="JSON array of learned facts"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "tone_style": self.tone_style,
            "response_length": self.response_length,
            "language_preference": self.language_preference,
            "theme": self.theme,
            "like_count": self.like_count,
            "dislike_count": self.dislike_count,
            "learned_facts": self.learned_facts,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }