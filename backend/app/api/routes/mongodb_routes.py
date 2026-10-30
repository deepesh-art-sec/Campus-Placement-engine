"""
MongoDB API Routes.
Provides administrative endpoints to check MongoDB database health,
test/update connection strings, view document collections, and trigger full database synchronization.
"""

from __future__ import annotations

import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.api.auth.dependencies import (
    get_current_user,
    require_officer,
    require_officer_or_coordinator,
)
from backend.app.api.logging.audit_service import AuditService
from backend.app.storage.database import get_db
from backend.app.storage.models.entities import UserModel
from backend.app.storage.mongodb import (
    MongoSyncService,
    close_mongodb,
    get_configured_db_name,
    get_configured_uri,
    get_mongo_client,
    get_mongo_db,
    get_mongodb_status,
    mask_mongo_uri,
    ping_mongodb,
)

router = APIRouter(prefix="/api/mongodb", tags=["MongoDB Database"])


class MongoConfigPayload(BaseModel):
    uri: str = Field(..., min_length=10, description="MongoDB connection string (e.g. mongodb://localhost:27017 or mongodb+srv://...)")
    database_name: str | None = Field(None, max_length=64, description="Target MongoDB database name")


@router.get("/status")
def get_status(
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieves current MongoDB connectivity, health latency, and document counts."""
    return get_mongodb_status()


@router.get("/ping")
def ping_database(
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    """Runs an active ping against the configured MongoDB database."""
    return ping_mongodb()


@router.post("/sync")
def trigger_full_sync(
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Performs full synchronization of all students, drives, attendance,
    eligibility decisions, schedules, and audit records into MongoDB collections.
    """
    try:
        report = MongoSyncService.sync_all(db)

        # Audit log the synchronization action
        AuditService.record_action(
            db=db,
            actor=current_user.username,
            action="MONGODB_FULL_SYNC",
            aggregate_type="DATABASE_SYNC",
            aggregate_id=report.get("database", "placement_engine"),
            payload={
                "total_documents": report.get("total_documents", 0),
                "collections": report.get("counts", {}),
            },
        )
        return report
    except ConnectionError as ce:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(ce),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"MongoDB synchronization failed: {e}",
        )


@router.post("/hydrate")
def trigger_hydrate(
    current_user: UserModel = Depends(require_officer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Hydrates SQLite database from MongoDB cloud store.
    Useful for cold boots, new nodes, or disaster recovery.
    """
    try:
        report = MongoSyncService.hydrate_sqlite_from_mongodb(db)
        AuditService.record_action(
            db=db,
            actor=current_user.username,
            action="MONGODB_HYDRATE_SQLITE",
            aggregate_type="DATABASE_HYDRATION",
            aggregate_id="sqlite",
            payload={"restored": report.get("counts", {})},
        )
        return report
    except ConnectionError as ce:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(ce))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Hydration failed: {e}")


@router.post("/configure")
def configure_mongodb(
    payload: MongoConfigPayload,
    current_user: UserModel = Depends(require_officer),  # Restricted to Placement Officer
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Tests and updates the MongoDB connection URI at runtime (e.g. connecting to cloud Atlas cluster).
    """
    import os
    import backend.app.storage.mongodb as mongo_mod

    raw_uri = payload.uri.strip()
    target_db = (payload.database_name or "").strip() or get_configured_db_name()

    # Test the connection before committing
    test_client = mongo_mod.get_mongo_client(uri=raw_uri, force_reconnect=True)
    if not test_client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to initialize MongoDB client with provided URI.",
        )

    try:
        test_client.admin.command("ping")
        server_info = test_client.server_info()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reach MongoDB with provided URI: {e}",
        )

    # Connection succeeded: persist in environment and runtime state
    os.environ["MONGODB_URL"] = raw_uri
    os.environ["MONGODB_DB_NAME"] = target_db
    mongo_mod._configured_uri = raw_uri

    AuditService.record_action(
        db=db,
        actor=current_user.username,
        action="MONGODB_CONFIGURED",
        aggregate_type="DATABASE_CONFIG",
        aggregate_id=target_db,
        payload={"masked_uri": mask_mongo_uri(raw_uri), "database": target_db},
    )

    return {
        "status": "connected",
        "message": "Successfully connected to MongoDB.",
        "uri": mask_mongo_uri(raw_uri),
        "database": target_db,
        "server_version": server_info.get("version"),
    }


@router.get("/collections")
def list_collections(
    current_user: UserModel = Depends(require_officer_or_coordinator),
) -> dict[str, Any]:
    """Lists all collections in the MongoDB database and their document counts."""
    db = get_mongo_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MongoDB is not currently connected at {mask_mongo_uri(get_configured_uri())}.",
        )

    try:
        colls = db.list_collection_names()
        details = {}
        for c in colls:
            details[c] = db[c].count_documents({})
        return {
            "database": get_configured_db_name(),
            "collections": details,
            "total_collections": len(colls),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query collections: {e}")


@router.get("/collections/{collection_name}")
def inspect_collection_documents(
    collection_name: str,
    limit: int = Query(default=20, le=100),
    skip: int = Query(default=0, ge=0),
    current_user: UserModel = Depends(require_officer_or_coordinator),
) -> dict[str, Any]:
    """Inspects documents stored in a specific MongoDB collection."""
    db = get_mongo_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MongoDB is not currently connected.",
        )

    try:
        cursor = db[collection_name].find({}).skip(skip).limit(limit)
        docs = []
        for d in cursor:
            # Convert _id if needed
            if "_id" in d:
                d["_id"] = str(d["_id"])
            docs.append(d)

        total = db[collection_name].count_documents({})
        return {
            "collection": collection_name,
            "total_count": total,
            "limit": limit,
            "skip": skip,
            "documents": docs,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to inspect collection: {e}")
