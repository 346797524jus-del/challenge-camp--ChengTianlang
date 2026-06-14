"""
Xiaoshitou Agent - Central Configuration
All sensitive values read from environment variables ONLY.
Supports MySQL with automatic SQLite fallback, Milvus RAG, MCP, DashScope.
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ━━━━ AI Model (DashScope / OpenAI-compatible) ━━━━
    ai_api_base_url: str = "https://api.deepseek.com/v1"
    ai_model_name: str = "deepseek-chat"
    ai_api_key: str = "sk-46f3e548c7774726b1c6a94da442a496"

    # ━━━━ DashScope (RAG + LLM fallback) ━━━━
    dashscope_api_key: str = "sk-46f3e548c7774726b1c6a94da442a496"
    llm_model: str = "qwen-plus"
    embedding_model: str = "text-embedding-v1"
    embedding_dim: int = 1536

    # ━━━━ MySQL Database ━━━━
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "Jus."
    mysql_password: str = "Just7524"
    mysql_database: str = "agent_memory"

    # ━━━━ Milvus Vector DB ━━━━
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_collection: str = "agent_rag"
    rag_similarity_threshold: float = 0.5

    # ━━━━ Knowledge Base ━━━━
    knowledge_base_url: str = "https://api.example.com/v1"
    knowledge_base_api_key: str = ""

    # ━━━━ Application ━━━━
    app_secret_key: str = "p3-agent-secret-key-change-in-production"
    app_port: int = 8081
    app_debug: bool = False

    # ━━━━ Feature Flags ━━━━
    search_enabled: bool = True  # Always on, user cannot toggle
    deep_thinking_default: bool = False

    # ━━━━ File Storage ━━━━
    upload_dir: str = "./workspace/files/uploads"
    generated_dir: str = "./workspace/files/generated"
    backup_dir: str = "./workspace/files/backups"

    # ━━━━ Redis Cache ━━━━
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # ━━━━ SQLite Fallback ━━━━
    sqlite_path: str = "./workspace/agent_memory.db"

    # ━━━━ MCP Servers Config ━━━━
    mcp_config_path: str = "./mcp/servers_config.json"

    # ━━━━ Xiaoshitou Identity ━━━━
    assistant_name: str = "小石头"
    assistant_default_avatar: str = "🪨"
    assistant_persona: str = "warm_professional"  # warm_professional, formal, humorous, concise

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def mysql_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            f"?charset=utf8mb4"
        )

    @property
    def sqlite_url(self) -> str:
        abs_path = str(BASE_DIR / self.sqlite_path)
        return f"sqlite:///{abs_path}"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Workspace directories
WORKSPACE_DIR = BASE_DIR / "workspace"
FILES_DIR = WORKSPACE_DIR / "files"
UPLOAD_DIR = FILES_DIR / "uploads"
GENERATED_DIR = FILES_DIR / "generated"
BACKUP_DIR = FILES_DIR / "backups"
MCP_DIR = BASE_DIR / "mcp"

for d in [WORKSPACE_DIR, FILES_DIR, UPLOAD_DIR, GENERATED_DIR, BACKUP_DIR, MCP_DIR]:
    d.mkdir(parents=True, exist_ok=True)