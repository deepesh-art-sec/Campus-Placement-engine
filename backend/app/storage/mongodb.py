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
from backend.app.storage.models.entities import (
    AcademicRecordModel,
    AttendanceRecordModel,
    AuditLogModel,
    BacklogModel,
    CompanyModel,
    CoordinatorRequestModel,
    DriveAttendanceModel,
    DriveModel,
    EligibilityDecisionModel,
    GapYearModel,
    NotificationModel,
    OfferModel,
    PanelModel,
    PolicyModel,
    RoomModel,
    ScheduleModel,
    SlotModel,
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
