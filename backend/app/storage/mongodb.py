"""
MongoDB Storage and Synchronization Engine for Campus Placement Platform.
Provides connection pooling, health checks, collection accessors,
and bidirectional sync between relational SQLite models and MongoDB document store.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import time
from typing import Any

from pymongo import MongoClient, UpdateOne
from pymongo.errors import ConnectionFailure, PyMongoError, ServerSelectionTimeoutError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

# Patch mongomock BulkOperationBuilder for compatibility with pymongo 4.19+ sort parameter
try:
    import mongomock.collection
    _orig_bulk_add_update = mongomock.collection.BulkOperationBuilder.add_update

    def _safe_bulk_add_update(self, *args, **kwargs):
        kwargs.pop("sort", None)
        return _orig_bulk_add_update(self, *args, **kwargs)

    mongomock.collection.BulkOperationBuilder.add_update = _safe_bulk_add_update
except Exception:
    pass

import logging

from pathlib import Path
try:
    from dotenv import load_dotenv
    _env_file = Path(__file__).resolve().parents[3] / '.env'
    if _env_file.exists():
        load_dotenv(dotenv_path=_env_file, override=True)
    else:
        load_dotenv()
except ImportError:
    pass
import queue
import threading
import uuid
from sqlalchemy import event
from backend.app.storage.models.entities import (
    AcademicRecordModel,
    AttendanceRecordModel,
    AuditLogModel,
    BacklogModel,
    CompanyModel,
    CoordinatorRequestModel,
    DriveAttendanceModel,
    DriveModel,
    DriveRequirementVersionModel,
    EligibilityDecisionModel,
    GapYearModel,
    NotificationModel,
    OfferModel,
    PanelModel,
    PolicyModel,
    RoomModel,
    ScheduleModel,
    SlotModel,
    StudentApplicationModel,
    StudentModel,
    UserModel,
)

logger = logging.getLogger("placement_mongodb")

# Default MongoDB configuration
DEFAULT_MONGO_URI = "mongodb://localhost:27017"
DEFAULT_MONGO_DB = "placement_engine"

_mongo_client: MongoClient | None = None
_configured_uri: str | None = None
_last_sync_time: str | None = None


def mask_mongo_uri(uri: str) -> str:
    """Masks credentials in MongoDB connection string for safe client display."""
    if not uri:
        return ""
    # Mask password in mongodb://user:pass@host or mongodb+srv://user:pass@host
    return re.sub(r"://([^:@]+):([^@]+)@", r"://\1:****@", uri)


def get_configured_uri() -> str:
    """Returns currently active MongoDB connection URI from memory or environment."""
    global _configured_uri
    if _configured_uri:
        return _configured_uri
    return os.getenv("MONGODB_URL") or os.getenv("MONGO_URI") or DEFAULT_MONGO_URI


def get_configured_db_name() -> str:
    """Returns currently active MongoDB database name."""
    return os.getenv("MONGODB_DB_NAME") or DEFAULT_MONGO_DB


def get_mongo_client(uri: str | None = None, force_reconnect: bool = False) -> MongoClient | None:
    """
    Returns cached MongoClient singleton.
    Uses short server selection timeouts (2s) to prevent blocking if MongoDB server is offline.
    """
    global _mongo_client, _configured_uri

    target_uri = uri or get_configured_uri()

    if force_reconnect and _mongo_client:
        try:
            _mongo_client.close()
        except Exception:
            pass
        _mongo_client = None

    if _mongo_client is None:
        try:
            _mongo_client = MongoClient(
                target_uri,
                serverSelectionTimeoutMS=4000,
                connectTimeoutMS=4000,
                socketTimeoutMS=5000,
            )
            _configured_uri = target_uri
        except Exception as e:
            logger.warning(f"Failed to instantiate MongoClient: {e}")
            return None

    return _mongo_client


def get_mongo_db(db_name: str | None = None) -> Any | None:
    """Returns MongoDB database instance if connected, otherwise None."""
    client = get_mongo_client()
    if not client:
        return None
    name = db_name or get_configured_db_name()
    try:
        return client[name]
    except Exception as e:
        logger.warning(f"Failed to access database {name}: {e}")
        return None


def is_mongodb_connected() -> bool:
    """Checks if MongoDB server is currently reachable."""
    client = get_mongo_client()
    if not client:
        return False
    try:
        client.admin.command("ping")
        return True
    except Exception:
        return False


def ping_mongodb() -> dict[str, Any]:
    """Runs a health check ping against MongoDB and returns diagnostics."""
    client = get_mongo_client()
    if not client:
        return {
            "connected": False,
            "error": "MongoClient not initialized",
            "uri": mask_mongo_uri(get_configured_uri()),
        }

    start = time.perf_counter()
    try:
        client.admin.command("ping")
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        server_info = client.server_info()
        version = server_info.get("version", "unknown")
        return {
            "connected": True,
            "latency_ms": latency_ms,
            "server_version": version,
            "uri": mask_mongo_uri(get_configured_uri()),
            "database": get_configured_db_name(),
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "uri": mask_mongo_uri(get_configured_uri()),
            "database": get_configured_db_name(),
        }


def close_mongodb() -> None:
    """Closes MongoClient on application shutdown."""
    global _mongo_client
    if _mongo_client:
        try:
            _mongo_client.close()
            logger.info("MongoDB connection closed cleanly.")
        except Exception as e:
            logger.warning(f"Error closing MongoClient: {e}")
        finally:
            _mongo_client = None


def ensure_mongodb_indexes() -> dict[str, list[str]]:
    """Configures performance indexes on MongoDB collections."""
    db = get_mongo_db()
    if db is None:
        return {}

    created = {}
    try:
        # Students indexes
        db.students.create_index("roll_no", unique=True)
        db.students.create_index("email")
        db.students.create_index("branch")
        db.students.create_index("cgpa")
        created["students"] = ["roll_no (unique)", "email", "branch", "cgpa"]

        # Drives indexes
        db.drives.create_index("id", unique=True)
        db.drives.create_index("company_name")
        db.drives.create_index("drive_date")
        created["drives"] = ["id (unique)", "company_name", "drive_date"]

        # Attendance indexes
        db.attendance.create_index([("drive_id", 1), ("student_id", 1), ("room_name", 1)])
        db.attendance.create_index("status")
        created["attendance"] = ["drive_id + student_id + room_name", "status"]

        # Eligibility Decisions
        db.eligibility_decisions.create_index([("drive_id", 1), ("student_id", 1)])
        created["eligibility_decisions"] = ["drive_id + student_id"]

        # Audit Logs
        db.audit_logs.create_index("timestamp")
        db.audit_logs.create_index("actor")
        created["audit_logs"] = ["timestamp", "actor"]

        # Notifications
        db.notifications.create_index([("recipient_role", 1), ("created_at", -1)])
        created["notifications"] = ["recipient_role + created_at"]
    except Exception as e:
        logger.warning(f"Failed to create some MongoDB indexes: {e}")

    return created



def _bulk_upsert(collection: Any, operations: list[UpdateOne], batch_size: int = 500) -> int:
    """
    Executes bulk upsert operations in batches.
    Gracefully falls back to individual updates for mongomock compatibility.
    """
    if not operations:
        return 0
    total = 0
    for i in range(0, len(operations), batch_size):
        batch = operations[i : i + batch_size]
        try:
            collection.bulk_write(batch, ordered=False)
            total += len(batch)
        except Exception:
            for op in batch:
                try:
                    collection.update_one(op._filter, op._doc, upsert=bool(op._upsert))
                    total += 1
                except Exception:
                    pass
    return total


class MongoSyncService:
    """
    Synchronizes entities between SQLite relational database and MongoDB document store.
    Supports full bulk synchronization as well as real-time individual entity updates.
    """

    @staticmethod
    def sync_all(db: Session) -> dict[str, Any]:
        """
        Extracts all records from SQLite and bulk upserts into MongoDB collections.
        Transforms relational models into rich, self-contained MongoDB documents.
        """
        global _last_sync_time
        mongo_db = get_mongo_db()
        if mongo_db is None:
            raise ConnectionError(
                f"Cannot sync: MongoDB is not reachable at {mask_mongo_uri(get_configured_uri())}."
            )

        ensure_mongodb_indexes()
        counts: dict[str, int] = {}
        now_iso = datetime.datetime.utcnow().isoformat()

        # 1. Sync Students (with embedded backlogs, academic records, offers, gap years)
        students_stmt = select(StudentModel).options(
            selectinload(StudentModel.backlogs),
            selectinload(StudentModel.academic_records),
            selectinload(StudentModel.offers),
            selectinload(StudentModel.gap_years),
        )
        students = db.execute(students_stmt).scalars().all()
        student_ops = []
        for s in students:
            doc = {
                "_id": s.id,
                "id": s.id,
                "roll_no": s.roll_no,
                "name": s.name,
                "normalized_name": s.normalized_name,
                "email": s.email,
                "branch": s.branch,
                "program": s.program,
                "cgpa": s.cgpa,
                "tenth_percentage": s.tenth_percentage,
                "twelfth_percentage": s.twelfth_percentage,
                "diploma_percentage": s.diploma_percentage,
                "date_of_birth": s.date_of_birth.isoformat() if s.date_of_birth else None,
                "gender": s.gender,
                "version": s.version,
                "backlogs": [
                    {
                        "subject": b.subject,
                        "semester": b.semester,
                        "status": b.status,
                        "cleared_on": b.cleared_on.isoformat() if b.cleared_on else None,
                    }
                    for b in (s.backlogs or [])
                ],
                "academic_records": [
                    {"semester": a.semester, "sgpa": a.sgpa}
                    for a in (s.academic_records or [])
                ],
                "offers": [
                    {
                        "company": getattr(o, "company", getattr(o, "company_name", "Company")),
                        "company_name": getattr(o, "company", getattr(o, "company_name", "Company")),
                        "ctc_lpa": getattr(o, "ctc_lpa", 0.0),
                        "fixed_pay_lpa": getattr(o, "fixed_pay_lpa", None),
                        "is_dream": getattr(o, "is_dream", False),
                        "status": getattr(o, "status", "offered"),
                    }
                    for o in (s.offers or [])
                ],
                "gap_years": [
                    {"duration_years": g.duration_years, "reason": g.reason}
                    for g in (s.gap_years or [])
                ],
                "synced_at": now_iso,
            }
            student_ops.append(UpdateOne({"_id": s.id}, {"$set": doc}, upsert=True))

        if student_ops:
            counts["students"] = _bulk_upsert(mongo_db.students, student_ops)

        # 2. Sync Companies
        companies = db.execute(select(CompanyModel)).scalars().all()
        comp_ops = []
        for c in companies:
            doc = {
                "_id": c.id,
                "id": c.id,
                "name": c.name,
                "tier": c.tier,
                "is_active": getattr(c, "is_active", True),
                "industry": getattr(c, "industry", None),
                "website": getattr(c, "website", None),
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "synced_at": now_iso,
            }
            comp_ops.append(UpdateOne({"_id": c.id}, {"$set": doc}, upsert=True))
        if comp_ops:
            counts["companies"] = _bulk_upsert(mongo_db.companies, comp_ops)

        # 3. Sync Drives
        drives = db.execute(select(DriveModel)).scalars().all()
        drive_ops = []
        for d in drives:
            doc = {
                "_id": d.id,
                "id": d.id,
                "company_id": d.company_id,
                "company_name": d.company_name,
                "job_role": getattr(d, "job_role", "Engineering Graduate Trainee"),
                "drive_date": d.drive_date.isoformat() if d.drive_date else None,
                "mode": d.mode,
                "ctc_lpa": d.ctc_lpa,
                "status": d.status,
                "version": d.version,
                "created_at": d.created_at.isoformat() if d.created_at else None,
                "synced_at": now_iso,
            }
            drive_ops.append(UpdateOne({"_id": d.id}, {"$set": doc}, upsert=True))
        if drive_ops:
            counts["drives"] = _bulk_upsert(mongo_db.drives, drive_ops)

        # 4. Sync Attendance Records (both DriveAttendanceModel and AttendanceRecordModel)
        att_records = db.execute(select(DriveAttendanceModel)).scalars().all()
        att_ops = []
        for a in att_records:
            doc = {
                "_id": a.id,
                "id": a.id,
                "drive_id": a.drive_id,
                "student_id": a.student_id,
                "slot_id": a.slot_id,
                "room_name": a.room_name,
                "status": a.status,
                "marked_by": a.marked_by,
                "marked_at": a.marked_at.isoformat() if a.marked_at else None,
                "notes": a.notes,
                "synced_at": now_iso,
            }
            att_ops.append(UpdateOne({"_id": a.id}, {"$set": doc}, upsert=True))
        if att_ops:
            counts["attendance"] = _bulk_upsert(mongo_db.attendance, att_ops)

        # 5. Sync Eligibility Decisions
        decisions = db.execute(select(EligibilityDecisionModel)).scalars().all()
        dec_ops = []
        for dec in decisions:
            doc = {
                "_id": dec.id,
                "id": dec.id,
                "drive_id": dec.drive_id,
                "student_id": dec.student_id,
                "status": dec.status,
                "reasons": json.loads(dec.reasons_json or "[]") if getattr(dec, "reasons_json", None) else [],
                "reason": getattr(dec, "reason", "Evaluated criteria"),
                "evaluated_at": dec.evaluated_at.isoformat() if dec.evaluated_at else None,
                "synced_at": now_iso,
            }
            dec_ops.append(UpdateOne({"_id": dec.id}, {"$set": doc}, upsert=True))
        if dec_ops:
            counts["eligibility_decisions"] = _bulk_upsert(mongo_db.eligibility_decisions, dec_ops)

        # 6. Sync Rooms & Panels
        rooms = db.execute(select(RoomModel)).scalars().all()
        room_ops = [
            UpdateOne(
                {"_id": r.id},
                {
                    "$set": {
                        "_id": r.id,
                        "name": r.name,
                        "building": r.building,
                        "capacity": r.capacity,
                        "synced_at": now_iso,
                    }
                },
                upsert=True,
            )
            for r in rooms
        ]
        if room_ops:
            counts["rooms"] = _bulk_upsert(mongo_db.rooms, room_ops)

        # 7. Sync Notifications
        notifs = db.execute(select(NotificationModel)).scalars().all()
        notif_ops = []
        for n in notifs:
            doc = {
                "_id": n.id,
                "id": n.id,
                "recipient_role": n.recipient_role,
                "recipient_username": n.recipient_username,
                "category": n.category,
                "title": n.title,
                "message": n.message,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat() if n.created_at else None,
                "metadata": json.loads(n.metadata_json or "{}"),
                "synced_at": now_iso,
            }
            notif_ops.append(UpdateOne({"_id": n.id}, {"$set": doc}, upsert=True))
        if notif_ops:
            counts["notifications"] = _bulk_upsert(mongo_db.notifications, notif_ops)

        # 8. Sync Policies
        policies = db.execute(select(PolicyModel)).scalars().all()
        policy_ops = []
        for p in policies:
            doc = {
                "_id": p.id,
                "id": p.id,
                "name": p.name,
                "version": getattr(p, "version", 1),
                "max_offers_per_student": getattr(p, "max_offers_per_student", 1),
                "dream_tier_ctc_lpa": getattr(p, "dream_tier_ctc_lpa", 10.0),
                "super_dream_tier_ctc_lpa": getattr(p, "super_dream_tier_ctc_lpa", 20.0),
                "allow_dream_upgrade": getattr(p, "allow_dream_upgrade", True),
                "upgrade_ctc_multiplier": getattr(p, "upgrade_ctc_multiplier", 1.5),
                "strict_backlog_cutoff": getattr(p, "strict_backlog_cutoff", True),
                "allow_multiple_offers_if_different_tiers": getattr(p, "allow_multiple_offers_if_different_tiers", True),
                "is_active": getattr(p, "is_active", True),
                "created_at": p.created_at.isoformat() if getattr(p, "created_at", None) else None,
                "synced_at": now_iso,
            }
            policy_ops.append(UpdateOne({"_id": p.id}, {"$set": doc}, upsert=True))
        if policy_ops:
            counts["policies"] = _bulk_upsert(mongo_db.policies, policy_ops)

        # 9. Sync Audit Logs
        audit_logs = db.execute(select(AuditLogModel).order_by(AuditLogModel.timestamp.desc()).limit(500)).scalars().all()
        audit_ops = []
        for a in audit_logs:
            doc = {
                "_id": a.id,
                "id": a.id,
                "actor": a.actor,
                "action": a.action,
                "entity_type": getattr(a, "entity_type", "AUDIT"),
                "entity_id": getattr(a, "entity_id", a.id),
                "changes": json.loads(a.changes_json or "{}") if getattr(a, "changes_json", None) else {},
                "timestamp": a.timestamp.isoformat() if getattr(a, "timestamp", None) else None,
                "synced_at": now_iso,
            }
            audit_ops.append(UpdateOne({"_id": a.id}, {"$set": doc}, upsert=True))
        if audit_ops:
            counts["audit_logs"] = _bulk_upsert(mongo_db.audit_logs, audit_ops)

        # 10. Sync Users
        users = db.execute(select(UserModel)).scalars().all()
        user_ops = []
        for u in users:
            doc = {
                "_id": u.id,
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "password_hash": u.password_hash,
                "role": u.role,
                "is_active": u.is_active,
                "student_id": u.student_id,
                "company_id": u.company_id,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "synced_at": now_iso,
            }
            user_ops.append(UpdateOne({"_id": u.id}, {"$set": doc}, upsert=True))
        if user_ops:
            counts["users"] = _bulk_upsert(mongo_db.users, user_ops)

        # 11. Sync Slots
        slots = db.execute(select(SlotModel)).scalars().all()
        slot_ops = []
        for sl in slots:
            doc = {
                "_id": sl.id,
                "id": sl.id,
                "schedule_id": sl.schedule_id,
                "drive_id": sl.drive_id,
                "student_id": sl.student_id,
                "round_number": sl.round_number,
                "room_id": sl.room_id,
                "panel_id": sl.panel_id,
                "start_time": sl.start_time.isoformat() if sl.start_time else None,
                "end_time": sl.end_time.isoformat() if sl.end_time else None,
                "created_at": sl.created_at.isoformat() if sl.created_at else None,
                "synced_at": now_iso,
            }
            slot_ops.append(UpdateOne({"_id": sl.id}, {"$set": doc}, upsert=True))
        if slot_ops:
            counts["slots"] = _bulk_upsert(mongo_db.slots, slot_ops)

        # 12. Sync Drive Requirements
        reqs = db.execute(select(DriveRequirementVersionModel)).scalars().all()
        req_ops = []
        for r in reqs:
            doc = {
                "_id": r.id,
                "id": r.id,
                "drive_id": r.drive_id,
                "version_number": r.version_number,
                "raw_source_text": r.raw_source_text,
                "parse_confidence": r.parse_confidence,
                "min_cgpa": r.min_cgpa,
                "min_tenth_percentage": r.min_tenth_percentage,
                "min_twelfth_percentage": r.min_twelfth_percentage,
                "min_diploma_percentage": r.min_diploma_percentage,
                "allowed_branches": json.loads(r.allowed_branches_json or "[]") if getattr(r, "allowed_branches_json", None) else [],
                "allowed_programs": json.loads(r.allowed_programs_json or "[]") if getattr(r, "allowed_programs_json", None) else [],
                "max_active_backlogs": r.max_active_backlogs,
                "allow_history_backlogs": r.allow_history_backlogs,
                "max_history_backlogs": r.max_history_backlogs,
                "max_gap_years": r.max_gap_years,
                "allow_gap_during_degree": r.allow_gap_during_degree,
                "custom_rules": json.loads(r.custom_rules_json or "{}") if getattr(r, "custom_rules_json", None) else {},
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "synced_at": now_iso,
            }
            req_ops.append(UpdateOne({"_id": r.id}, {"$set": doc}, upsert=True))
        if req_ops:
            counts["drive_requirements"] = _bulk_upsert(mongo_db.drive_requirements, req_ops)

        # 13. Sync Coordinator Requests
        creqs = db.execute(select(CoordinatorRequestModel)).scalars().all()
        creq_ops = []
        for cr in creqs:
            doc = {
                "_id": cr.id,
                "id": cr.id,
                "request_type": cr.request_type,
                "title": cr.title,
                "description": cr.description,
                "submitted_by": cr.submitted_by,
                "submitted_at": cr.submitted_at.isoformat() if cr.submitted_at else None,
                "status": cr.status,
                "target_id": cr.target_id,
                "payload": json.loads(cr.payload_json or "{}") if getattr(cr, "payload_json", None) else {},
                "officer_response": cr.officer_response,
                "officer_name": cr.officer_name,
                "resolved_at": cr.resolved_at.isoformat() if cr.resolved_at else None,
                "comments": json.loads(cr.comments_json or "[]") if getattr(cr, "comments_json", None) else [],
                "synced_at": now_iso,
            }
            creq_ops.append(UpdateOne({"_id": cr.id}, {"$set": doc}, upsert=True))
        if creq_ops:
            counts["coordinator_requests"] = _bulk_upsert(mongo_db.coordinator_requests, creq_ops)

        # 14. Sync Applications
        apps = db.execute(select(StudentApplicationModel)).scalars().all()
        app_ops = []
        for ap in apps:
            doc = {
                "_id": ap.id,
                "id": ap.id,
                "student_id": ap.student_id,
                "drive_id": ap.drive_id,
                "status": ap.status,
                "applied_at": ap.applied_at.isoformat() if ap.applied_at else None,
                "notes": ap.notes,
                "synced_at": now_iso,
            }
            app_ops.append(UpdateOne({"_id": ap.id}, {"$set": doc}, upsert=True))
        if app_ops:
            counts["applications"] = _bulk_upsert(mongo_db.applications, app_ops)

        _last_sync_time = now_iso
        total_synced = sum(counts.values())

        logger.info(f"MongoDB full sync completed. Synced {total_synced} documents across {len(counts)} collections.")

        return {
            "status": "success",
            "message": f"Successfully synchronized {total_synced} documents to MongoDB.",
            "synced_at": now_iso,
            "counts": counts,
            "total_documents": total_synced,
            "database": get_configured_db_name(),
        }

    @staticmethod
    def sync_document(collection_name: str, doc_id: str, data: dict[str, Any]) -> bool:
        """
        Lightweight hook to mirror individual writes to MongoDB in real time.
        Silently returns False if MongoDB is disconnected without throwing errors.
        """
        try:
            mongo_db = get_mongo_db()
            if mongo_db is None:
                return False
            data["synced_at"] = datetime.datetime.utcnow().isoformat()
            mongo_db[collection_name].update_one({"_id": doc_id}, {"$set": data}, upsert=True)
            return True
        except Exception as e:
            logger.debug(f"Optional MongoDB mirror failed for {collection_name}/{doc_id}: {e}")
            return False



    @staticmethod
    def hydrate_sqlite_from_mongodb(db: Session) -> dict[str, Any]:
        """
        Reconstructs relational SQLite records from MongoDB documents.
        Enables instant recovery, cloud deployment hydration (e.g. Vercel /tmp),
        and zero-loss synchronization when SQLite starts fresh.
        """
        mongo_db = get_mongo_db()
        if mongo_db is None:
            raise ConnectionError("Cannot hydrate: MongoDB is not connected.")

        counts = {}

        # 1. Hydrate Users
        user_docs = list(mongo_db.users.find({}))
        user_count = 0
        for doc in user_docs:
            uid = doc.get("id") or str(doc.get("_id"))
            if not db.query(UserModel).filter_by(id=uid).first():
                u = UserModel(
                    id=uid,
                    username=doc.get("username"),
                    email=doc.get("email"),
                    password_hash=doc.get("password_hash"),
                    role=doc.get("role", "student"),
                    is_active=doc.get("is_active", True),
                    student_id=doc.get("student_id"),
                    company_id=doc.get("company_id"),
                )
                db.add(u)
                user_count += 1
        db.commit()
        counts["users"] = user_count

        # 2. Hydrate Policies
        policy_docs = list(mongo_db.policies.find({}))
        pol_count = 0
        for doc in policy_docs:
            pid = doc.get("id") or str(doc.get("_id"))
            if not db.query(PolicyModel).filter_by(id=pid).first():
                p = PolicyModel(
                    id=pid,
                    name=doc.get("name", "Default Policy"),
                    version=doc.get("version", 1),
                    max_offers_per_student=doc.get("max_offers_per_student", 1),
                    dream_tier_ctc_lpa=doc.get("dream_tier_ctc_lpa", 10.0),
                    super_dream_tier_ctc_lpa=doc.get("super_dream_tier_ctc_lpa", 20.0),
                    allow_dream_upgrade=doc.get("allow_dream_upgrade", True),
                    upgrade_ctc_multiplier=doc.get("upgrade_ctc_multiplier", 1.5),
                    strict_backlog_cutoff=doc.get("strict_backlog_cutoff", True),
                    allow_multiple_offers_if_different_tiers=doc.get("allow_multiple_offers_if_different_tiers", True),
                    is_active=doc.get("is_active", True),
                )
                db.add(p)
                pol_count += 1
        db.commit()
        counts["policies"] = pol_count

        # 3. Hydrate Companies
        comp_docs = list(mongo_db.companies.find({}))
        comp_count = 0
        for doc in comp_docs:
            cid = doc.get("id") or str(doc.get("_id"))
            if not db.query(CompanyModel).filter_by(id=cid).first():
                c = CompanyModel(
                    id=cid,
                    name=doc.get("name"),
                    industry=doc.get("industry"),
                    tier=doc.get("tier", "Regular"),
                    website=doc.get("website"),
                )
                db.add(c)
                comp_count += 1
        db.commit()
        counts["companies"] = comp_count

        # 4. Hydrate Rooms
        room_docs = list(mongo_db.rooms.find({}))
        room_count = 0
        for doc in room_docs:
            rid = doc.get("id") or str(doc.get("_id"))
            if not db.query(RoomModel).filter_by(id=rid).first():
                r = RoomModel(
                    id=rid,
                    name=doc.get("name"),
                    building=doc.get("building"),
                    capacity=doc.get("capacity", 30),
                )
                db.add(r)
                room_count += 1
        db.commit()
        counts["rooms"] = room_count

        # 5. Hydrate Drives
        drive_docs = list(mongo_db.drives.find({}))
        drv_count = 0
        for doc in drive_docs:
            did = doc.get("id") or str(doc.get("_id"))
            if not db.query(DriveModel).filter_by(id=did).first():
                dd = None
                if doc.get("drive_date"):
                    try:
                        dd = datetime.datetime.fromisoformat(doc["drive_date"])
                    except Exception:
                        pass
                d = DriveModel(
                    id=did,
                    company_id=doc.get("company_id"),
                    company_name=doc.get("company_name"),
                    drive_date=dd,
                    mode=doc.get("mode", "in_person"),
                    ctc_lpa=doc.get("ctc_lpa", 0.0),
                    status=doc.get("status", "scheduled"),
                )
                db.add(d)
                drv_count += 1
        db.commit()
        counts["drives"] = drv_count

        # 6. Hydrate Students + embedded collections
        stud_docs = list(mongo_db.students.find({}))
        stud_count = 0
        for doc in stud_docs:
            sid = doc.get("id") or str(doc.get("_id"))
            if not db.query(StudentModel).filter_by(id=sid).first():
                dob = None
                if doc.get("date_of_birth"):
                    try:
                        dob = datetime.date.fromisoformat(doc["date_of_birth"])
                    except Exception:
                        pass
                s = StudentModel(
                    id=sid,
                    roll_no=doc.get("roll_no"),
                    name=doc.get("name"),
                    normalized_name=doc.get("normalized_name"),
                    email=doc.get("email"),
                    branch=doc.get("branch"),
                    program=doc.get("program"),
                    cgpa=doc.get("cgpa", 0.0),
                    tenth_percentage=doc.get("tenth_percentage", 0.0),
                    twelfth_percentage=doc.get("twelfth_percentage", 0.0),
                    diploma_percentage=doc.get("diploma_percentage"),
                    date_of_birth=dob,
                    gender=doc.get("gender"),
                    version=doc.get("version", 1),
                )
                db.add(s)
                # Embedded backlogs
                for b_doc in doc.get("backlogs", []):
                    b = BacklogModel(
                        id=f"bkl_{uuid.uuid4().hex[:12]}",
                        student_id=sid,
                        subject=b_doc.get("subject"),
                        semester=b_doc.get("semester", 1),
                        status=b_doc.get("status", "cleared"),
                    )
                    db.add(b)
                # Embedded academic records
                for a_doc in doc.get("academic_records", []):
                    ar = AcademicRecordModel(
                        id=f"rec_{uuid.uuid4().hex[:12]}",
                        student_id=sid,
                        semester=a_doc.get("semester", 1),
                        sgpa=a_doc.get("sgpa", 0.0),
                    )
                    db.add(ar)
                # Embedded offers
                for o_doc in doc.get("offers", []):
                    off = OfferModel(
                        id=f"off_{uuid.uuid4().hex[:12]}",
                        student_id=sid,
                        company=o_doc.get("company") or o_doc.get("company_name", "Company"),
                        ctc_lpa=o_doc.get("ctc_lpa", 0.0),
                        fixed_pay_lpa=o_doc.get("fixed_pay_lpa"),
                        is_dream=o_doc.get("is_dream", False),
                        status=o_doc.get("status", "offered"),
                    )
                    db.add(off)
                stud_count += 1
        db.commit()
        counts["students"] = stud_count

        # 7. Hydrate Slots
        slot_docs = list(mongo_db.slots.find({}))
        slot_count = 0
        for doc in slot_docs:
            slid = doc.get("id") or str(doc.get("_id"))
            if not db.query(SlotModel).filter_by(id=slid).first():
                st = None
                et = None
                if doc.get("start_time"):
                    try:
                        st = datetime.datetime.fromisoformat(doc["start_time"])
                    except Exception:
                        pass
                if doc.get("end_time"):
                    try:
                        et = datetime.datetime.fromisoformat(doc["end_time"])
                    except Exception:
                        pass
                sl = SlotModel(
                    id=slid,
                    schedule_id=doc.get("schedule_id"),
                    drive_id=doc.get("drive_id"),
                    student_id=doc.get("student_id"),
                    round_number=doc.get("round_number", 1),
                    room_id=doc.get("room_id"),
                    panel_id=doc.get("panel_id"),
                    start_time=st,
                    end_time=et,
                )
                db.add(sl)
                slot_count += 1
        db.commit()
        counts["slots"] = slot_count

        total_hydrated = sum(counts.values())
        logger.info(f"SQLite hydrated from MongoDB Atlas: {total_hydrated} records restored.")
        return {
            "status": "success",
            "message": f"Successfully hydrated {total_hydrated} records from MongoDB Atlas.",
            "counts": counts,
            "total_restored": total_hydrated,
        }


# ==============================================================================
# REAL-TIME ASYNCHRONOUS WRITE-MIRROR QUEUE & LISTENER
# ==============================================================================

_sync_queue: queue.Queue = queue.Queue(maxsize=10000)
_worker_running: bool = False
_worker_thread: threading.Thread | None = None
_listener_attached: bool = False


def _extract_model_for_mongo(obj: Any) -> tuple[str, str, dict[str, Any]] | None:
    """Serializes SQLAlchemy model instances into collection name, ID, and dictionary."""
    if not hasattr(obj, "id") or not obj.id:
        return None

    doc_id = str(obj.id)
    now_iso = datetime.datetime.utcnow().isoformat()

    if isinstance(obj, StudentModel):
        return (
            "students",
            doc_id,
            {
                "_id": doc_id,
                "id": doc_id,
                "roll_no": obj.roll_no,
                "name": obj.name,
                "normalized_name": obj.normalized_name,
                "email": obj.email,
                "branch": obj.branch,
                "program": obj.program,
                "cgpa": obj.cgpa,
                "tenth_percentage": obj.tenth_percentage,
                "twelfth_percentage": obj.twelfth_percentage,
                "diploma_percentage": obj.diploma_percentage,
                "date_of_birth": obj.date_of_birth.isoformat() if obj.date_of_birth else None,
                "gender": obj.gender,
                "version": obj.version,
                "synced_at": now_iso,
            },
        )
    elif isinstance(obj, DriveModel):
        return (
            "drives",
            doc_id,
            {
                "_id": doc_id,
                "id": doc_id,
                "company_id": obj.company_id,
                "company_name": obj.company_name,
                "drive_date": obj.drive_date.isoformat() if obj.drive_date else None,
                "mode": obj.mode,
                "ctc_lpa": obj.ctc_lpa,
                "status": obj.status,
                "version": obj.version,
                "synced_at": now_iso,
            },
        )
    elif isinstance(obj, CompanyModel):
        return (
            "companies",
            doc_id,
            {
                "_id": doc_id,
                "id": doc_id,
                "name": obj.name,
                "tier": obj.tier,
                "industry": getattr(obj, "industry", None),
                "website": getattr(obj, "website", None),
                "synced_at": now_iso,
            },
        )
    elif isinstance(obj, SlotModel):
        return (
            "slots",
            doc_id,
            {
                "_id": doc_id,
                "id": doc_id,
                "schedule_id": obj.schedule_id,
                "drive_id": obj.drive_id,
                "student_id": obj.student_id,
                "round_number": obj.round_number,
                "room_id": obj.room_id,
                "panel_id": obj.panel_id,
                "start_time": obj.start_time.isoformat() if obj.start_time else None,
                "end_time": obj.end_time.isoformat() if obj.end_time else None,
                "synced_at": now_iso,
            },
        )
    elif isinstance(obj, PolicyModel):
        return (
            "policies",
            doc_id,
            {
                "_id": doc_id,
                "id": doc_id,
                "name": obj.name,
                "version": getattr(obj, "version", 1),
                "max_offers_per_student": getattr(obj, "max_offers_per_student", 1),
                "dream_tier_ctc_lpa": getattr(obj, "dream_tier_ctc_lpa", 10.0),
                "super_dream_tier_ctc_lpa": getattr(obj, "super_dream_tier_ctc_lpa", 20.0),
                "allow_dream_upgrade": getattr(obj, "allow_dream_upgrade", True),
                "upgrade_ctc_multiplier": getattr(obj, "upgrade_ctc_multiplier", 1.5),
                "strict_backlog_cutoff": getattr(obj, "strict_backlog_cutoff", True),
                "allow_multiple_offers_if_different_tiers": getattr(obj, "allow_multiple_offers_if_different_tiers", True),
                "is_active": getattr(obj, "is_active", True),
                "synced_at": now_iso,
            },
        )
    elif isinstance(obj, RoomModel):
        return (
            "rooms",
            doc_id,
            {
                "_id": doc_id,
                "id": doc_id,
                "name": obj.name,
                "building": obj.building,
                "capacity": obj.capacity,
                "synced_at": now_iso,
            },
        )
    elif isinstance(obj, UserModel):
        return (
            "users",
            doc_id,
            {
                "_id": doc_id,
                "id": doc_id,
                "username": obj.username,
                "email": obj.email,
                "password_hash": obj.password_hash,
                "role": obj.role,
                "is_active": obj.is_active,
                "student_id": obj.student_id,
                "company_id": obj.company_id,
                "synced_at": now_iso,
            },
        )
    elif isinstance(obj, DriveAttendanceModel):
        return (
            "attendance",
            doc_id,
            {
                "_id": doc_id,
                "id": doc_id,
                "drive_id": obj.drive_id,
                "student_id": obj.student_id,
                "slot_id": obj.slot_id,
                "room_name": obj.room_name,
                "status": obj.status,
                "marked_by": obj.marked_by,
                "marked_at": obj.marked_at.isoformat() if obj.marked_at else None,
                "notes": obj.notes,
                "synced_at": now_iso,
            },
        )
    elif isinstance(obj, EligibilityDecisionModel):
        return (
            "eligibility_decisions",
            doc_id,
            {
                "_id": doc_id,
                "id": doc_id,
                "drive_id": obj.drive_id,
                "student_id": obj.student_id,
                "status": obj.status,
                "reasons": json.loads(obj.reasons_json or "[]") if getattr(obj, "reasons_json", None) else [],
                "reason": getattr(obj, "reason", "Evaluated criteria"),
                "evaluated_at": obj.evaluated_at.isoformat() if obj.evaluated_at else None,
                "synced_at": now_iso,
            },
        )
    elif isinstance(obj, NotificationModel):
        return (
            "notifications",
            doc_id,
            {
                "_id": doc_id,
                "id": doc_id,
                "recipient_role": obj.recipient_role,
                "recipient_username": obj.recipient_username,
                "category": obj.category,
                "title": obj.title,
                "message": obj.message,
                "is_read": obj.is_read,
                "created_at": obj.created_at.isoformat() if obj.created_at else None,
                "synced_at": now_iso,
            },
        )
    elif isinstance(obj, AuditLogModel):
        return (
            "audit_logs",
            doc_id,
            {
                "_id": doc_id,
                "id": doc_id,
                "actor": obj.actor,
                "action": obj.action,
                "entity_type": getattr(obj, "entity_type", "AUDIT"),
                "entity_id": getattr(obj, "entity_id", obj.id),
                "changes": json.loads(obj.changes_json or "{}") if getattr(obj, "changes_json", None) else {},
                "timestamp": obj.timestamp.isoformat() if getattr(obj, "timestamp", None) else None,
                "synced_at": now_iso,
            },
        )
    elif isinstance(obj, CoordinatorRequestModel):
        return (
            "coordinator_requests",
            doc_id,
            {
                "_id": doc_id,
                "id": doc_id,
                "request_type": obj.request_type,
                "title": obj.title,
                "description": obj.description,
                "submitted_by": obj.submitted_by,
                "submitted_at": obj.submitted_at.isoformat() if obj.submitted_at else None,
                "status": obj.status,
                "target_id": obj.target_id,
                "officer_response": obj.officer_response,
                "officer_name": obj.officer_name,
                "resolved_at": obj.resolved_at.isoformat() if obj.resolved_at else None,
                "synced_at": now_iso,
            },
        )
    return None


def _mongo_sync_worker():
    """Background worker continuously pulling from _sync_queue to mirror writes to MongoDB."""
    while True:
        try:
            item = _sync_queue.get()
            if item is None:
                break
            coll_name, doc_id, doc_data = item
            mongo_db = get_mongo_db()
            if mongo_db is not None:
                doc_data["synced_at"] = datetime.datetime.utcnow().isoformat()
                mongo_db[coll_name].update_one({"_id": doc_id}, {"$set": doc_data}, upsert=True)
            _sync_queue.task_done()
        except Exception as e:
            logger.debug(f"Background MongoDB sync worker error: {e}")
            time.sleep(0.5)


def start_mongo_sync_worker():
    global _worker_running, _worker_thread
    if not _worker_running:
        _worker_running = True
        _worker_thread = threading.Thread(target=_mongo_sync_worker, daemon=True, name="MongoSyncWorker")
        _worker_thread.start()
        logger.info("MongoDB background real-time sync worker started.")


def enable_realtime_mongo_sync():
    """Attaches SQLAlchemy event listeners to mirror every database commit to MongoDB."""
    global _listener_attached
    if _listener_attached:
        return
    start_mongo_sync_worker()

    @event.listens_for(Session, "after_flush")
    def capture_flush(session, flush_context):
        pending = session.info.setdefault("_mongo_pending", [])
        for obj in list(session.new) + list(session.dirty):
            extracted = _extract_model_for_mongo(obj)
            if extracted:
                pending.append(extracted)

    @event.listens_for(Session, "after_commit")
    def enqueue_commit(session):
        pending = session.info.pop("_mongo_pending", [])
        for coll_name, doc_id, data in pending:
            try:
                _sync_queue.put_nowait((coll_name, doc_id, data))
            except queue.Full:
                logger.warning(f"Mongo sync queue full; dropped async write for {coll_name}/{doc_id}")

    _listener_attached = True
    logger.info("SQLAlchemy -> MongoDB real-time write mirror active.")


def get_mongodb_status() -> dict[str, Any]:
    """Retrieves connection health, database metrics, and collection counts from MongoDB."""
    ping = ping_mongodb()
    status_report: dict[str, Any] = {
        "configured_uri": mask_mongo_uri(get_configured_uri()),
        "database": get_configured_db_name(),
        "connected": ping.get("connected", False),
        "latency_ms": ping.get("latency_ms"),
        "server_version": ping.get("server_version"),
        "error": ping.get("error"),
        "last_sync_time": _last_sync_time,
        "collections": {},
        "total_documents": 0,
    }

    if ping.get("connected", False):
        try:
            db = get_mongo_db()
            if db is not None:
                coll_names = [
                    "students",
                    "offers",
                    "backlogs",
                    "companies",
                    "drives",
                    "drive_requirements",
                    "rooms",
                    "policies",
                    "users",
                    "announcements",
                    "attendance",
                    "eligibility_decisions",
                    "notifications",
                    "audit_logs",
                ]
                counts = {}
                total = 0
                for c_name in coll_names:
                    try:
                        c_count = db[c_name].count_documents({})
                        counts[c_name] = c_count
                        total += c_count
                    except Exception:
                        counts[c_name] = 0
                status_report["collections"] = counts
                status_report["total_documents"] = total
        except Exception as e:
            status_report["collection_error"] = str(e)

    return status_report
