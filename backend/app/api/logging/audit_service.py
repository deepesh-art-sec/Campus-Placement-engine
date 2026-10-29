"""
Institutional Audit Logging Service.
Records every student data access and every export event for governance compliance.
"""

from __future__ import annotations

import datetime
import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from backend.app.storage.models.entities import AuditLogModel


class AuditService:
    """Manages compliance audit trails for data privacy and institutional accountability."""

    @staticmethod
    def record_student_access(
        db: Session,
        actor: str,
        student_id: str,
        action: str = "VIEW",
        endpoint: str = "",
        details: dict[str, Any] | None = None,
    ) -> AuditLogModel:
        """Records an access event to an individual student's records."""
        payload = {
            "endpoint": endpoint,
            "access_type": action,
            "details": details or {},
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }
        entry = AuditLogModel(
            id=str(uuid.uuid4()),
            entity_type="STUDENT_RECORD",
            entity_id=student_id,
            action=action,
            actor=actor,
            changes_json=json.dumps(payload),
            timestamp=datetime.datetime.utcnow(),
        )
        db.add(entry)
        db.commit()
        return entry

    @staticmethod
    def record_export(
        db: Session,
        actor: str,
        export_type: str,
        company_id: str | None = None,
        candidate_count: int = 0,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> AuditLogModel:
        """Records an institutional roster or schedule data export."""
        meta = metadata or {}
        if kwargs:
            meta.update(kwargs)
        if "row_count" in kwargs and not candidate_count:
            candidate_count = kwargs["row_count"]

        payload = {
            "export_type": export_type,
            "company_id": company_id,
            "candidate_count": candidate_count,
            "metadata": meta,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }
        entry = AuditLogModel(
            id=str(uuid.uuid4()),
            entity_type="DATA_EXPORT",
            entity_id=company_id or export_type,
            action="EXPORT",
            actor=actor,
            changes_json=json.dumps(payload),
            timestamp=datetime.datetime.utcnow(),
        )
        db.add(entry)
        db.commit()
        return entry

    @staticmethod
    def record_action(
        db: Session,
        actor: str,
        action: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict[str, Any] | None = None,
    ) -> AuditLogModel:
        """Records an action in the audit log."""
        entry = AuditLogModel(
            id=str(uuid.uuid4()),
            entity_type=aggregate_type,
            entity_id=aggregate_id,
            action=action,
            actor=actor,
            changes_json=json.dumps(payload or {}),
            timestamp=datetime.datetime.utcnow(),
        )
        db.add(entry)
        db.commit()
        return entry

    @staticmethod
    def record_event(
        db: Session,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict[str, Any],
        actor_id: str,
        actor_role: str,
    ) -> AuditLogModel:
        """Records a generic institutional administrative or security event."""
        entry = AuditLogModel(
            id=str(uuid.uuid4()),
            entity_type=aggregate_type,
            entity_id=aggregate_id,
            action=event_type,
            actor=f"{actor_role}:{actor_id}",
            changes_json=json.dumps(payload),
            timestamp=datetime.datetime.utcnow(),
        )
        db.add(entry)
        db.commit()
        return entry
