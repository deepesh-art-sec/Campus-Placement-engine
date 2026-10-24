"""
Central FastAPI Application Entrypoint.
Production-grade institutional placement eligibility and scheduling backend.
"""

from __future__ import annotations

import hmac
import os
import socket
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.staticfiles import StaticFiles

from backend.app.api.auth.csrf import CSRF_COOKIE_NAME
from backend.app.api.auth.seeder import seed_default_accounts
from backend.app.api.logging.logger import get_logger
from backend.app.api.routes import (
    audit_routes,
    auth_routes,
    backup_routes,
    compare_routes,
    drive_routes,
    eligibility_routes,
    event_routes,
    export_routes,
    extract_routes,
    imats_routes,
    policy_routes,
    publish_routes,
    recruiter_routes,
    schedule_routes,
    student_routes,
    what_if_routes,
)

logger = get_logger("placement_api")


def _get_lan_ip() -> str:
    """Detects active physical LAN IPv4 address without making outbound internet connections."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        if ip and not ip.startswith("127.") and not ip.startswith("169.254."):
            return ip
    except Exception:
        pass
    finally:
        s.close()
    try:
        hostname = socket.gethostname()
        candidates = socket.gethostbyname_ex(hostname)[2]
        for ip in candidates:
            if not ip.startswith(("127.", "169.254.", "192.168.65.", "192.168.83.")):
                return ip
        for ip in candidates:
            if not ip.startswith(("127.", "169.254.")):
                return ip
    except Exception:
        pass
    return "127.0.0.1"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context for startup initialization."""
    seed_default_accounts()
    logger.info("Placement Engine API initialized successfully.")
    yield


app = FastAPI(
    title="Institutional Placement Eligibility & Scheduling Engine",
    description="Offline collegiate placement eligibility evaluation, live offer policy enforcement, clash-free scheduling, and audit replay system.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for college LAN deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next: Callable[..., Any]) -> Response:
    """Enforces strict offline security headers, CSP, and upload body limits."""
    # Enforce 15 MB upload limit
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 15 * 1024 * 1024:
        return JSONResponse(
            status_code=413,
            content={"detail": "Payload Too Large: File upload exceeds 15 MB institutional limit."},
        )

    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )
    return response


@app.middleware("http")
async def csrf_middleware(request: Request, call_next: Callable[..., Any]) -> Response:
    """Validates CSRF tokens on state-mutating requests (POST, PUT, DELETE, PATCH)."""
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        path = request.url.path
        if not path.startswith(("/docs", "/openapi.json", "/api/auth/login", "/api/auth/student-login", "/api/auth/logout", "/api/auth/csrf")):
            cookie_csrf = request.cookies.get(CSRF_COOKIE_NAME)
            header_csrf = request.headers.get("X-CSRF-Token")
            if cookie_csrf:
                if not header_csrf or not hmac.compare_digest(cookie_csrf, header_csrf):
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "CSRF token mismatch. Potential cross-site request forgery rejected."},
                    )

    response: Response = await call_next(request)
    return response


# Include Routers
app.include_router(auth_routes.router)
app.include_router(student_routes.router)
app.include_router(drive_routes.router)
app.include_router(policy_routes.router)
app.include_router(extract_routes.router)
app.include_router(eligibility_routes.router)
app.include_router(schedule_routes.router)
app.include_router(what_if_routes.router)
app.include_router(publish_routes.router)
app.include_router(event_routes.router)
app.include_router(compare_routes.router)
app.include_router(audit_routes.router)
app.include_router(export_routes.router)
app.include_router(recruiter_routes.router)
app.include_router(imats_routes.router)
app.include_router(backup_routes.router)


@app.get("/api/health")
def health_check() -> dict[str, str]:
    """Lightweight LAN ping check."""
    return {"status": "healthy", "service": "PlacementEngine"}


@app.get("/api/lan-info")
def lan_info() -> dict[str, Any]:
    """Returns server LAN IPv4 address and shareable URLs for campus network."""
    ip = _get_lan_ip()
    return {
        "primary_ip": ip,
        "primary_url": f"http://{ip}:8000",
        "port": 8000,
    }


# -----------------------------------------------------------------------------
# Static App Shell & SPA Serving for Single-Port LAN Deployment
# -----------------------------------------------------------------------------
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../frontend/dist"))
if os.path.exists(frontend_dist):
    assets_dir = os.path.join(frontend_dist, "assets")

    @app.get("/assets/{asset_file:path}")
    async def serve_asset(asset_file: str) -> Response:
        """Serves compiled assets with stale-hash fallback for cached browsers."""
        target_path = os.path.join(assets_dir, asset_file)
        if os.path.exists(target_path) and os.path.isfile(target_path):
            return FileResponse(
                target_path,
                headers={"Cache-Control": "public, max-age=31536000, immutable"},
            )
        # Stale cache recovery: If browser has older HTML requesting an older hash
        if os.path.exists(assets_dir):
            if asset_file.endswith(".js"):
                js_files = [f for f in os.listdir(assets_dir) if f.endswith(".js")]
                if js_files:
                    return FileResponse(
                        os.path.join(assets_dir, js_files[0]),
                        media_type="application/javascript",
                        headers={"Cache-Control": "no-cache"},
                    )
            elif asset_file.endswith(".css"):
                css_files = [f for f in os.listdir(assets_dir) if f.endswith(".css")]
                if css_files:
                    return FileResponse(
                        os.path.join(assets_dir, css_files[0]),
                        media_type="text/css",
                        headers={"Cache-Control": "no-cache"},
                    )
        raise HTTPException(status_code=404, detail="Asset not found")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str) -> Response:
        """Serves compiled frontend SPA for all non-API paths."""
        if full_path.startswith(("api/", "docs", "openapi.json")):
            raise HTTPException(status_code=404, detail="Resource Not Found")
        target_file = os.path.join(frontend_dist, full_path)
        if full_path and os.path.exists(target_file) and os.path.isfile(target_file):
            resp = FileResponse(target_file)
            if full_path in ("sw.js", "favicon.ico", "manifest.json"):
                resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return resp
        resp = FileResponse(os.path.join(frontend_dist, "index.html"))
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp
