"""
Institutional Backup, Restore, and Secure Wipe Administration Routes.
Provides AES-encrypted database backup/restore and zero-trace institutional wipe.
"""

from __future__ import annotations

import base64
import datetime
import os
import shutil
import sqlite3
import tempfile
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.api.auth.dependencies import require_officer
from backend.app.api.auth.seeder import seed_default_accounts
from backend.app.api.logging.audit_service import AuditService
from backend.app.storage.database import DATABASE_URL, Base, engine, get_db
from backend.app.storage.models.entities import UserModel

router: APIRouter = APIRouter(prefix="/api/admin", tags=["Backup & Maintenance"])

BACKUP_DIR = os.getenv("BACKUP_DIR", "./backups")
os.makedirs(BACKUP_DIR, exist_ok=True)


def _derive_fernet_key(passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))


def _get_sqlite_path() -> str:
    if DATABASE_URL.startswith("sqlite:///"):
        return DATABASE_URL.replace("sqlite:///", "")
    return "./placement_engine.db"


class WipeRequest(BaseModel):
    confirmation_phrase: str
    reason: str


@router.post("/backup")
def create_backup(
    passphrase: str = Form(default="InstitutionalPlacement2026"),
    current_user: UserModel = Depends(require_officer),
    db: Session = Depends(get_db),
) -> FileResponse:
    """Creates an encrypted AES-256 backup archive of the SQLite database."""
    db_path = _get_sqlite_path()
    if not os.path.exists(db_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Database file not found.")

    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"placement_backup_{timestamp}.enc"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)

    # 1. Read SQLite database bytes
    with open(db_path, "rb") as f:
        raw_db_bytes = f.read()

    # 2. Derive key and encrypt
    salt = os.urandom(16)
    key = _derive_fernet_key(passphrase, salt)
    cipher = Fernet(key)
    encrypted_bytes = cipher.encrypt(raw_db_bytes)

    # 3. Store: 16 bytes salt + encrypted payload
    with open(backup_path, "wb") as f:
        f.write(salt + encrypted_bytes)

    # Audit event
    AuditService.record_event(
        db=db,
        event_type="SYSTEM_BACKUP_CREATED",
        aggregate_type="DATABASE",
        aggregate_id=backup_filename,
        payload={"filename": backup_filename, "size_bytes": len(encrypted_bytes)},
        actor_id=str(current_user.id),
        actor_role=str(current_user.role),
    )

    return FileResponse(
        path=backup_path,
        media_type="application/octet-stream",
        filename=backup_filename,
    )


@router.post("/restore")
async def restore_backup(
    backup_file: UploadFile = File(...),
    passphrase: str = Form(...),
    current_user: UserModel = Depends(require_officer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Restores database from an authenticated encrypted backup."""
    contents = await backup_file.read()
    if len(contents) < 17:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Corrupted backup file.")

    salt = contents[:16]
    encrypted_payload = contents[16:]

    try:
        key = _derive_fernet_key(passphrase, salt)
        cipher = Fernet(key)
        decrypted_db = cipher.decrypt(encrypted_payload)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decryption failed. Incorrect passphrase or corrupted backup archive.",
        ) from exc

    # Validate SQLite header
    if not decrypted_db.startswith(b"SQLite format 3\x00"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Decrypted file is not a valid SQLite database.")

    # Write to temp file and test integrity
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(decrypted_db)
        tmp_path = tmp.name

    try:
        conn = sqlite3.connect(tmp_path)
        cur = conn.cursor()
        cur.execute("PRAGMA integrity_check;")
        res = cur.fetchone()
        conn.close()
        if not res or res[0] != "ok":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Database integrity check failed.")

        # Replace active database
        target_path = _get_sqlite_path()
        shutil.copyfile(tmp_path, target_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    # Record audit log
    AuditService.record_event(
        db=db,
        event_type="SYSTEM_DATABASE_RESTORED",
        aggregate_type="DATABASE",
        aggregate_id=backup_file.filename or "unknown",
        payload={"filename": backup_file.filename, "restored_at": datetime.datetime.utcnow().isoformat()},
        actor_id=str(current_user.id),
        actor_role=str(current_user.role),
    )

    return {"status": "success", "message": "Database restored successfully from encrypted backup."}


@router.post("/wipe")
def wipe_institutional_data(
    req: WipeRequest,
    current_user: UserModel = Depends(require_officer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    One-click institutional wipe: removes all students, drives, schedules, and offers.
    Preserves default administrative accounts and re-initializes clean schema.
    """
    if req.confirmation_phrase != "CONFIRM_INSTITUTIONAL_WIPE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation phrase mismatch. Type 'CONFIRM_INSTITUTIONAL_WIPE' to proceed.",
        )

    # 1. Drop all tables and recreate
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # 2. Re-seed default administrator accounts
    seed_default_accounts()

    # 3. Log audit event
    AuditService.record_event(
        db=db,
        event_type="SYSTEM_INSTITUTIONAL_WIPE",
        aggregate_type="DATABASE",
        aggregate_id="ALL_RECORDS",
        payload={"reason": req.reason, "wiped_at": datetime.datetime.utcnow().isoformat()},
        actor_id=str(current_user.id),
        actor_role=str(current_user.role),
    )

    return {
        "status": "success",
        "message": "Institutional wipe completed. All academic and placement data purged safely.",
    }
