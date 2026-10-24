"""
Cross-Site Request Forgery (CSRF) Protection.
Provides cryptographically secure anti-CSRF token generation and validation.
"""

from __future__ import annotations

import hmac
import secrets

from fastapi import HTTPException, Request, status

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"


def generate_csrf_token() -> str:
    """Generates a high-entropy URL-safe CSRF token."""
    return secrets.token_urlsafe(32)


def verify_csrf_token(request: Request) -> None:
    """
    Validates CSRF token on state-mutating requests (POST, PUT, DELETE, PATCH).
    Excludes initial authentication endpoints that issue tokens.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    # Skip login and initial auth routes
    if request.url.path in ("/api/auth/login", "/api/auth/student-login", "/api/auth/csrf"):
        return

    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    header_token = request.headers.get(CSRF_HEADER_NAME)

    if not cookie_token or not header_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing from request cookie or header.",
        )

    if not hmac.compare_digest(cookie_token, header_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token mismatch. Potential cross-site request forgery rejected.",
        )
