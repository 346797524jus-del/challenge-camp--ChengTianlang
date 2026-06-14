"""Message model - individual chat messages within a session."""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Boolean, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Message(Base):
    """Chat message belonging to a session."""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(
        String(20), comment="user, assistant, system"
    )
    content: Mapped[str] = mapped_column(Text(length=50000))
    content_type: Mapped[str] = mapped_column(
        String(20), default="text", comment="text, file, image, code"
    )
    # Message interaction feedback
    feedback: Mapped[str] = mapped_column(
        String(20), default="", comment="like, dislike, or empty"
    )
    # Branch tracking
    parent_message_id: Mapped[str] = mapped_column(
        String(36), default="", comment="For branch creation tracking"
    )
    branch_session_id: Mapped[str] = mapped_column(
        String(36), default="", comment="If branched, new session ID"
    )
    # Token count for summary tracking
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    # Ordering within session
    sequence: Mapped[int] = mapped_column(Integer, default=0, comment="Message order in session")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    # Relationships
    session = relationship("Session", back_populates="messages")

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "content_type": self.content_type,
            "feedback": self.feedback,
            "parent_message_id": self.parent_message_id,
            "branch_session_id": self.branch_session_id,
            "sequence": self.sequence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }