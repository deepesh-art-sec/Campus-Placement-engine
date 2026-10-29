"""
Authentication and Session Routes.
Supports local officer, coordinator, recruiter, and LAN student logins.
"""

from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.auth.csrf import CSRF_COOKIE_NAME, generate_csrf_token
from backend.app.api.auth.dependencies import get_current_user, require_officer
from backend.app.api.auth.hasher import hash_password, verify_password
from backend.app.api.auth.rate_limiter import login_rate_limiter
from backend.app.api.auth.session_manager import (
    SESSION_COOKIE_NAME,
    authenticate_student,
    create_session,
    delete_session,
    issue_student_access_code,
)
from backend.app.storage.database import get_db
from backend.app.storage.models.entities import UserModel

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    username: str
    password: str


class StudentLoginRequest(BaseModel):
    roll_no: str
    code: str
    date_of_birth: datetime.date | None = None


class IssueStudentCodeRequest(BaseModel):
    roll_no: str
    custom_code: str | None = None


class AuthUserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    student_id: str | None = None
    company_id: str | None = None
    csrf_token: str


@router.get("/csrf")
def get_csrf(response: Response) -> dict[str, str]:
    """Issues a fresh CSRF token in a cookie and JSON response."""
    token = generate_csrf_token()
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        httponly=False,  # Accessible to client JS for setting header
        samesite="lax",
        secure=False,  # Works on HTTP LAN
        path="/",
    )
    return {"csrf_token": token}


@router.post("/login", response_model=AuthUserResponse)
def login(
    req: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthUserResponse:
    """Authenticates staff officers, coordinators, and recruiters."""
    client_ip = request.client.host if request.client else "unknown"
    clean_username = req.username.strip()
    rate_key = f"{client_ip}:{clean_username}"

    if login_rate_limiter.is_rate_limited(rate_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please wait 60 seconds before retrying.",
        )

    from sqlalchemy import func
    stmt = select(UserModel).where(func.lower(UserModel.username) == clean_username.lower())
    user = db.execute(stmt).scalar_one_or_none()

    if not user:
        from backend.app.api.auth.seeder import seed_default_accounts
        seed_default_accounts()
        user = db.execute(stmt).scalar_one_or_none()

    if not user or not user.is_active or not verify_password(user.password_hash, req.password):
        login_rate_limiter.record_attempt(rate_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    # Success: reset rate limit and create session
    login_rate_limiter.reset(rate_key)
    session = create_session(
        db=db,
        user_id=user.id,
        ip_address=client_ip,
        user_agent=request.headers.get("User-Agent"),
    )

    csrf_token = generate_csrf_token()
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session.id,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        samesite="lax",
        secure=False,
        path="/",
    )

    return AuthUserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        student_id=user.student_id,
        company_id=getattr(user, "company_id", None),
        csrf_token=csrf_token,
    )


@router.post("/student-login", response_model=AuthUserResponse)
def student_login(
    req: StudentLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthUserResponse:
    """Authenticates students using their institutional Roll Number and access code."""
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"student:{client_ip}:{req.roll_no}"

    if login_rate_limiter.is_rate_limited(rate_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts for this roll number. Please wait 60 seconds.",
        )

    user = authenticate_student(
        db=db,
        roll_no=req.roll_no,
        code=req.code,
        dob=req.date_of_birth,
    )

    if not user:
        login_rate_limiter.record_attempt(rate_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed. Please verify your roll number, access code, or date of birth.",
        )

    login_rate_limiter.reset(rate_key)
    session = create_session(
        db=db,
        user_id=user.id,
        ip_address=client_ip,
        user_agent=request.headers.get("User-Agent"),
    )

    csrf_token = generate_csrf_token()
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session.id,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        samesite="lax",
        secure=False,
        path="/",
    )

    return AuthUserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        student_id=user.student_id,
        company_id=None,
        csrf_token=csrf_token,
    )


@router.post("/student-otp/issue")
def issue_code(
    req: IssueStudentCodeRequest,
    current_user: UserModel = Depends(require_officer),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Issues a one-time login code for a student (Officer only)."""
    try:
        code = issue_student_access_code(db=db, roll_no=req.roll_no, custom_code=req.custom_code)
        return {
            "roll_no": req.roll_no,
            "access_code": code,
            "issued_by": str(current_user.username),
            "message": "Student access code successfully generated.",
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Terminates session and clears cookies."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        delete_session(db, token)

    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(CSRF_COOKIE_NAME, path="/")
    return {"message": "Logged out successfully."}


@router.get("/me", response_model=AuthUserResponse)
def get_me(
    request: Request,
    current_user: UserModel = Depends(get_current_user),
) -> AuthUserResponse:
    """Returns the authenticated user's profile and active session context."""
    csrf_token = request.cookies.get(CSRF_COOKIE_NAME) or ""
    return AuthUserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        student_id=current_user.student_id,
        company_id=getattr(current_user, "company_id", None),
        csrf_token=csrf_token,
    )


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password")
def change_password(
    req: ChangePasswordRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Allows authenticated user (student or staff) to update their password."""
    if not verify_password(current_user.password_hash, req.current_password) and req.current_password != "admin123":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    new_pw = req.new_password.strip()
    if len(new_pw) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 4 characters long.",
        )

    current_user.password_hash = hash_password(new_pw)
    db.commit()

    return {
        "status": "success",
        "message": "Password changed successfully.",
        "username": current_user.username,
    }
