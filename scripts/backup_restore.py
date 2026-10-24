"""
Administrative CLI Script for Database Maintenance: Encrypted Backup, Restore, and Wipe.
Supports offline air-gapped placement operations.
"""

from __future__ import annotations

import argparse
import base64
import datetime
import os
import shutil
import sqlite3
import sys
import tempfile

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def derive_key(passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))


def backup_database(db_path: str, output_path: str, passphrase: str) -> None:
    if not os.path.exists(db_path):
        print(f"[ERROR] Database file not found at: {db_path}")
        sys.exit(1)

    print(f"[*] Reading database from: {db_path}")
    with open(db_path, "rb") as f:
        data = f.read()

    salt = os.urandom(16)
    key = derive_key(passphrase, salt)
    cipher = Fernet(key)
    encrypted = cipher.encrypt(data)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(salt + encrypted)

    print(f"[SUCCESS] Encrypted backup created at: {output_path} ({len(salt + encrypted)} bytes)")


def restore_database(backup_path: str, target_db_path: str, passphrase: str) -> None:
    if not os.path.exists(backup_path):
        print(f"[ERROR] Backup archive not found at: {backup_path}")
        sys.exit(1)

    print(f"[*] Reading encrypted backup: {backup_path}")
    with open(backup_path, "rb") as f:
        content = f.read()

    salt = content[:16]
    encrypted_data = content[16:]

    try:
        key = derive_key(passphrase, salt)
        cipher = Fernet(key)
        decrypted = cipher.decrypt(encrypted_data)
    except Exception as exc:
        print(f"[ERROR] Decryption failed: {exc}. Please verify passphrase.")
        sys.exit(1)

    # Verify SQLite format
    if not decrypted.startswith(b"SQLite format 3\x00"):
        print("[ERROR] Corrupted archive: Decrypted content is not a SQLite database.")
        sys.exit(1)

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(decrypted)
        tmp_name = tmp.name

    conn = sqlite3.connect(tmp_name)
    cur = conn.cursor()
    cur.execute("PRAGMA integrity_check;")
    check = cur.fetchone()
    conn.close()

    if not check or check[0] != "ok":
        print(f"[ERROR] SQLite integrity check failed: {check}")
        os.remove(tmp_name)
        sys.exit(1)

    shutil.copyfile(tmp_name, target_db_path)
    os.remove(tmp_name)
    print(f"[SUCCESS] Database safely restored to: {target_db_path}")


def wipe_database(db_path: str) -> None:
    confirm = input("Are you ABSOLUTELY SURE you want to purge all records? Type 'CONFIRM_WIPE': ")
    if confirm != "CONFIRM_WIPE":
        print("[ABORTED] Confirmation mismatch. Wipe cancelled.")
        sys.exit(1)

    from backend.app.api.main import seed_default_accounts
    from backend.app.storage.database import Base, engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_default_accounts()
    print("[SUCCESS] Institutional database wiped cleanly and default accounts re-seeded.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Institutional Placement Engine Data Maintenance CLI")
    parser.add_argument("--backup", action="store_true", help="Create encrypted backup")
    parser.add_argument("--restore", action="store_true", help="Restore from encrypted backup")
    parser.add_argument("--wipe", action="store_true", help="One-click institutional wipe")
    parser.add_argument("--db", default="./placement_engine.db", help="Path to SQLite database")
    parser.add_argument("--file", help="Path to .enc backup archive")
    parser.add_argument("--passphrase", default="InstitutionalPlacement2026", help="Backup encryption passphrase")

    args = parser.parse_args()

    if args.backup:
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        out = args.file or f"./backups/placement_backup_{ts}.enc"
        backup_database(args.db, out, args.passphrase)
    elif args.restore:
        if not args.file:
            print("[ERROR] Please provide --file <path_to_backup.enc>")
            sys.exit(1)
        restore_database(args.file, args.db, args.passphrase)
    elif args.wipe:
        wipe_database(args.db)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
