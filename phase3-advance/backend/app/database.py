"""
Database engine with automatic MySQL → SQLite fallback.
P3 Agent System requires persistent storage. MySQL is primary.
If MySQL connection fails, automatically falls back to local SQLite.
"""
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import QueuePool, StaticPool
from app.config import get_settings
from loguru import logger


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


_settings = get_settings()
_db_type = "unknown"
_connection_string = ""

def _create_engine():
    """Try MySQL first, fall back to SQLite with full functionality."""
    global _db_type, _connection_string

    # ━━━ Attempt 1: MySQL ━━━
    try:
        logger.info(f"Attempting MySQL connection: {_settings.mysql_host}:{_settings.mysql_port}/{_settings.mysql_database}")
        eng = create_engine(
            _settings.mysql_url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_recycle=3600,
            pool_pre_ping=True,
            echo=False,
        )
        # Test connection
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        _db_type = "MySQL"
        _connection_string = f"mysql://{_settings.mysql_host}:{_settings.mysql_port}/{_settings.mysql_database}"
        logger.info(f"✅ Connected to MySQL: {_connection_string}")
        return eng
    except Exception as e:
        logger.warning(f"⚠️ MySQL connection failed: {e}")
        logger.warning("Falling back to SQLite for persistent local storage...")

    # ━━━ Attempt 2: SQLite ━━━
    try:
        sqlite_path = _settings.sqlite_path
        sqlite_url = _settings.sqlite_url
        logger.info(f"Attempting SQLite connection: {sqlite_path}")
        eng = create_engine(
            sqlite_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        _db_type = "SQLite"
        _connection_string = f"sqlite:///{sqlite_path}"
        logger.info(f"✅ Connected to SQLite: {sqlite_path}")
        return eng
    except Exception as e:
        logger.error(f"❌ SQLite also failed: {e}")
        logger.error("No database available. Creating in-memory SQLite as last resort.")
        eng = create_engine("sqlite:///:memory:", echo=False)
        _db_type = "SQLite (memory)"
        _connection_string = "sqlite:///:memory:"
        return eng


def get_db_info() -> dict:
    """Return current database connection info for diagnostics."""
    return {
        "type": _db_type,
        "connection": _connection_string,
        "status": "connected" if engine else "disconnected",
    }


# Initialize engine
engine = _create_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    """Dependency: provide a DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables if they don't exist yet."""
    from app.models import (
        session, message, preference, knowledge, file_record,
    )
    Base.metadata.create_all(bind=engine)
    info = get_db_info()
    logger.info(f"✅ Database tables ready ({info['type']}: {info['connection']})")
    return info


