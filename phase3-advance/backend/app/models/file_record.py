"""FileRecord model - tracks uploaded and generated files per session."""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Integer, Float, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class FileRecord(Base):
    """File uploaded or generated within a session."""

    __tablename__ = "file_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(500))
    original_filename: Mapped[str] = mapped_column(String(500))
    file_path: Mapped[str] = mapped_column(String(1000))
    file_type: Mapped[str] = mapped_column(
        String(50), comment="pdf, docx, xlsx, csv, txt, png, jpg, pptx"
    )
    file_size: Mapped[int] = mapped_column(Integer, default=0, comment="Size in bytes")
    purpose: Mapped[str] = mapped_column(
        String(50), default="upload", comment="upload, generated, processed"
    )
    content_preview: Mapped[str] = mapped_column(
        Text(length=5000), default="", comment="First 500 chars of parsed content"
    )
    # Processing metadata
    processed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, default=0, comment="For tabular files")
    status: Mapped[str] = mapped_column(
        String(20), default="uploaded", comment="uploaded, parsed, processing, done, error"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    # Relationships
    session = relationship("Session", back_populates="files")

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "purpose": self.purpose,
            "content_preview": self.content_preview,
            "row_count": self.row_count,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }