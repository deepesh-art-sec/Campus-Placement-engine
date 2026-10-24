"""
Pytest configuration and test fixtures.
Provides an isolated, in-memory SQLite database configured with foreign keys and WAL mode.
"""

from collections.abc import Generator

# Preload ortools native DLLs before pandas/openpyxl to guarantee clean Windows DLL resolution
try:
    from ortools.sat.python import cp_model as _cp_model  # noqa: F401
except Exception:
    pass

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

import backend.app.storage.models  # noqa: F401
from backend.app.storage.database import Base
from backend.app.storage.repositories.sqlalchemy_repo import SqlAlchemyUnitOfWork


@pytest.fixture
def test_engine() -> Engine:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection: object, connection_record: object) -> None:
        if hasattr(dbapi_connection, "cursor"):
            cursor = dbapi_connection.cursor()  # type: ignore
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def db_session(test_engine: Engine) -> Generator[Session, None, None]:
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def test_uow(test_engine: Engine) -> SqlAlchemyUnitOfWork:
    session_factory = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    return SqlAlchemyUnitOfWork(session_factory)
