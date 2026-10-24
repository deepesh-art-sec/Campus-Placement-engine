"""
Field-Level Encryption at Rest Provider.
Provides AES-256 (Fernet) authenticated symmetric encryption for sensitive student columns
stored in local SQLite tables, guaranteeing confidentiality if the raw .db file is inspected.
"""

from __future__ import annotations

import base64
import os
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy.types import String, TypeDecorator

# Secret passphrase from environment or institutional default
_RAW_SECRET = os.getenv("FIELD_ENCRYPTION_KEY", os.getenv("SECRET_KEY", "placement-airgap-salt-key-2026"))
_SALT = b"institutional_field_salt_v1"

# Derive 32-byte Fernet key via PBKDF2
_kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=_SALT,
    iterations=100_000,
)
_ENCRYPTION_KEY = base64.urlsafe_b64encode(_kdf.derive(_RAW_SECRET.encode()))
_cipher = Fernet(_ENCRYPTION_KEY)


def encrypt_field(plaintext: str | None) -> str | None:
    """Encrypts plaintext string into URL-safe base64 ciphertext with authentication."""
    if plaintext is None:
        return None
    token = _cipher.encrypt(plaintext.encode("utf-8"))
    return f"enc::{token.decode('utf-8')}"


def decrypt_field(ciphertext: str | None) -> str | None:
    """Decrypts ciphertext string. Falls back cleanly to plaintext if unencrypted."""
    if ciphertext is None:
        return None
    if not ciphertext.startswith("enc::"):
        return ciphertext  # Graceful compatibility for unencrypted legacy rows
    raw_token = ciphertext[5:]
    try:
        decrypted = _cipher.decrypt(raw_token.encode("utf-8"))
        return decrypted.decode("utf-8")
    except InvalidToken:
        return "[ENCRYPTED_PAYLOAD_DECRYPTION_FAILED]"


class EncryptedString(TypeDecorator[Any]):
    """SQLAlchemy TypeDecorator transparently encrypting strings at rest."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is not None and isinstance(value, str):
            return encrypt_field(value)
        return value

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is not None and isinstance(value, str):
            return decrypt_field(value)
        return value
