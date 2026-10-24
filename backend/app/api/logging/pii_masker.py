"""
PII Masking and Redaction Engine.
Guarantees student names, emails, dates of birth, and protected attributes
never leak into application logs or telemetry streams.
"""

from __future__ import annotations

import re
from typing import Any

# Sensitive field name patterns
PII_FIELD_PATTERNS = {
    "name",
    "student_name",
    "candidate_name",
    "email",
    "email_id",
    "date_of_birth",
    "dob",
    "phone",
    "mobile",
    "password",
    "password_hash",
    "gender",
    "caste",
    "religion",
    "category",
    "demographics",
}

EMAIL_REGEX = re.compile(r"([a-zA-Z0-9_.+-]+)@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)")


def mask_string(val: str, field_name: str | None = None) -> str:
    """Masks a sensitive string value."""
    if not val:
        return ""

    if field_name and field_name.lower() in ("password", "password_hash"):
        return "[REDACTED_SECRET]"

    if field_name and field_name.lower() in ("gender", "caste", "religion", "category"):
        return "[PROTECTED_ATTRIBUTE_SUPPRESSED]"

    if "@" in val:
        match = EMAIL_REGEX.match(val)
        if match:
            user_part, domain_part = match.groups()
            masked_user = user_part[0] + "***" if len(user_part) > 1 else "*"
            return f"{masked_user}@{domain_part}"

    if len(val) <= 4:
        return "***"

    return f"{val[:2]}***{val[-2:]}"


def mask_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively traverses a dictionary and redacts any PII or sensitive keys."""
    masked: dict[str, Any] = {}
    for key, value in data.items():
        key_lower = key.lower()
        if key_lower in PII_FIELD_PATTERNS:
            if isinstance(value, str):
                masked[key] = mask_string(value, field_name=key_lower)
            elif value is None:
                masked[key] = None
            else:
                masked[key] = "[REDACTED_PII]"
        elif isinstance(value, dict):
            masked[key] = mask_dict(value)
        elif isinstance(value, list):
            masked[key] = [mask_dict(item) if isinstance(item, dict) else item for item in value]
        else:
            masked[key] = value
    return masked
