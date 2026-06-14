"""Knowledge model - structured knowledge documents for RAG retrieval."""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Float, Integer, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class KnowledgeItem(Base):
    """Knowledge base entry with embedding support for RAG."""

    __tablename__ = "knowledge_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(500), comment="Document title")
    content: Mapped[str] = mapped_column(Text(length=50000))
    source_url: Mapped[str] = mapped_column(
        String(1000), default="", comment="URL of original source"
    )
    source_type: Mapped[str] = mapped_column(
        String(50), default="manual", comment="manual, web, file, api"
    )
    category: Mapped[str] = mapped_column(
        String(100), default="general", index=True
    )
    tags: Mapped[str] = mapped_column(
        String(500), default="", comment="Comma-separated tags"
    )
    # Embedding data (stored externally or as text)
    embedding_id: Mapped[str] = mapped_column(
        String(200), default="", comment="ID in vector store"
    )
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "source_url": self.source_url,
            "source_type": self.source_type,
            "category": self.category,
            "tags": self.tags,
            "relevance_score": self.relevance_score,
            "access_count": self.access_count,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class KnowledgeCache(Base):
    """Cache for frequently accessed knowledge base queries."""

    __tablename__ = "knowledge_cache"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    query_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    query_text: Mapped[str] = mapped_column(String(1000))
    result_json: Mapped[str] = mapped_column(Text(length=50000))
    hit_count: Mapped[int] = mapped_column(Integer, default=1)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )