"""
Database connection and session management.
Ensures SQLite WAL mode, foreign key constraint enforcement, busy timeouts, and robust connection pooling.
"""

import os
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./placement_engine.db")

# Vercel Serverless environment compatibility:
# AWS Lambda root (/var/task) is read-only. When running on Vercel with SQLite, copy
# the seeded database into temp storage so that write operations (auth, sessions, updates) succeed.
if (os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME")) and DATABASE_URL.startswith("sqlite"):
    import shutil
    import tempfile
    from pathlib import Path

    tmp_dir = Path(tempfile.gettempdir())
    tmp_db = tmp_dir / "placement_engine.db"
    if not tmp_db.exists():
        candidates = [
            Path(os.getcwd()) / "placement_engine.db",
            Path(__file__).resolve().parents[3] / "placement_engine.db",
            Path("/var/task/placement_engine.db"),
        ]
        for src in candidates:
            if src.exists():
                try:
                    shutil.copy2(src, tmp_db)
                    break
                except Exception:
                    pass
    if tmp_db.exists():
        DATABASE_URL = f"sqlite:///{tmp_db.as_posix()}"

# For SQLite, ensure connection arguments for multithreading and robust busy timeouts
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False, "timeout": 60.0}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=os.getenv("DEBUG", "false").lower() == "true",
)


# SQLite PRAGMA configuration: WAL mode, foreign keys, synchronous normal, memory cache & busy timeout
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection: object, connection_record: object) -> None:
    # Check if SQLite connection
    if hasattr(dbapi_connection, "cursor"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA busy_timeout=60000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=-64000")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """Dependency for API route handlers with automatic transaction rollback on errors."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
