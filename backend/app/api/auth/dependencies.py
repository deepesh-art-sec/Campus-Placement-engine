"""
FastAPI Authentication, RBAC, and UnitOfWork Dependencies.
"""

from __future__ import annotations

from collections.abc import Callable, Generator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.app.api.auth.session_manager import SESSION_COOKIE_NAME, get_session
from backend.app.storage.database import SessionLocal, get_db
from backend.app.storage.models.entities import UserModel
from backend.app.storage.repositories.sqlalchemy_repo import SqlAlchemyUnitOfWork


def get_uow() -> Generator[SqlAlchemyUnitOfWork, None, None]:
    """Dependency supplying a Unit of Work context."""
    uow = SqlAlchemyUnitOfWork(SessionLocal)
    yield uow


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> UserModel:
    """
    Extracts and authenticates the current user from the session cookie
    or Bearer authorization header.
    """
    token = request.cookies.get(SESSION_COOKIE_NAME)

    # Fallback to Authorization header for programmatic / testing access
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. No active session token found.",
        )

    session = get_session(db, token)
    if not session or not session.user or not session.user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or is invalid. Please log in again.",
        )

    return session.user


def require_role(allowed_roles: list[str]) -> Callable[[UserModel], UserModel]:
    """Factory creating an RBAC role verification dependency."""

    def role_checker(user: UserModel = Depends(get_current_user)) -> UserModel:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. User role '{user.role}' is not authorized for this operation.",
            )
        return user

    return role_checker


# Canonical Role Dependencies
require_officer = require_role(["officer"])
require_officer_or_coordinator = require_role(["officer", "coordinator"])
require_student = require_role(["student"])
require_recruiter = require_role(["recruiter", "recruiter_readonly"])
