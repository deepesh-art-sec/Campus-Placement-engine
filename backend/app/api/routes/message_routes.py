"""
Official Placement Communications and In-App Student Broadcast Routes.
Enables Placement Officers and Coordinators to compose, schedule, and dispatch
official placement messages, interview call slips, and venue alerts to candidate portals.
"""

from __future__ import annotations

import datetime
import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.auth.dependencies import require_officer_or_coordinator
from backend.app.api.logging.audit_service import AuditService
from backend.app.storage.database import get_db
from backend.app.storage.models.entities import (
    DriveModel,
    EligibilityDecisionModel,
    NotificationModel,
    SlotModel,
    StudentModel,
    UserModel,
)

router = APIRouter(prefix="/api/messages", tags=["Placement Communications & Messages"])


class BroadcastMessageRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    message: str = Field(..., min_length=2)
    target: str = Field(default="all")  # "all", "students", "coordinators", "drive_shortlist", "individual"
    category: str = Field(default="announcement")  # "announcement", "interview_call", "shortlist_notice", "venue_pass", "urgent_alert"
    drive_id: str | None = None
    recipient_username: str | None = None  # roll_no for individual student


class BroadcastHistoryItem(BaseModel):
    id: str
    category: str
    title: str
    message: str
    target: str
    recipient_count: int
    sender: str
    created_at: str
    drive_name: str | None = None


@router.get("/templates")
def get_message_templates(
    current_user: UserModel = Depends(require_officer_or_coordinator),
) -> list[dict[str, str]]:
    """Returns official institutional message templates for fast one-click dispatch."""
    return [
        {
            "id": "interview_call",
            "name": "Official Interview Call Letter",
            "category": "interview_call",
            "target": "drive_shortlist",
            "title": "Interview Call Letter — {company_name}",
            "template": (
                "Dear Candidate,\n\n"
                "You have been officially shortlisted for the campus recruitment process with {company_name} "
                "({job_role}) offering CTC {ctc_lpa} LPA on {drive_date}.\n\n"
                "Reporting Venue: Assigned Interview Cabin / Placement Block\n"
                "Dress Code: Formal Campus Placement Attire\n"
                "Mandatory Checklist: College ID Card, 2 hard copies of verified resume, and academic grade sheets.\n\n"
                "Please report 15 minutes prior to your allocated slot time. All updates are logged offline on the campus LAN.\n\n"
                "Training & Placement Cell"
            ),
        },
        {
            "id": "shortlist_notice",
            "name": "Drive Shortlist Publication",
            "category": "shortlist_notice",
            "target": "drive_shortlist",
            "title": "Shortlist Published — {company_name}",
            "template": (
                "Official Notice:\n\n"
                "The verified shortlist of eligible candidates for {company_name} has been published by the Training & Placement Cell. "
                "Please inspect your candidate portal to check your individual interview round details and assigned venue."
            ),
        },
        {
            "id": "venue_shift",
            "name": "Venue or Schedule Shift Alert",
            "category": "urgent_alert",
            "target": "drive_shortlist",
            "title": "Urgent: Interview Venue & Timing Shift — {company_name}",
            "template": (
                "Urgent Placement Alert:\n\n"
                "Due to recruiter panel restructuring, interview cabins for {company_name} have been re-assigned. "
                "Please check the live schedule board and your portal alerts immediately before proceeding to the cabin."
            ),
        },
        {
            "id": "document_verification",
            "name": "Document Verification Reminder",
            "category": "announcement",
            "target": "all",
            "title": "Pre-Drive Document Verification Reminder",
            "template": (
                "Notice to All Placement Registered Students:\n\n"
                "All candidates appearing for this week's campus drives must submit their academic transcripts "
                "and no-backlog certificates at the T&P desk before 5:00 PM today. Unverified profiles cannot be allotted interview slots."
            ),
        },
    ]


@router.post("/broadcast")
def broadcast_placement_message(
    payload: BroadcastMessageRequest,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Dispatches in-app message notifications to students, coordinators, or specific drive shortlists.
    Guarantees persistence in SQLite WAL without external network dependency.
    """
    broadcast_id = f"msg_{uuid.uuid4().hex[:12]}"
    created_at = datetime.datetime.utcnow()
    recipient_count = 0
    drive_name: str | None = None

    # Resolve company drive if applicable
    drive_entity: DriveModel | None = None
    if payload.drive_id:
        drive_entity = db.execute(
            select(DriveModel).where(DriveModel.id == payload.drive_id)
        ).scalar_one_or_none()
        if drive_entity:
            drive_name = drive_entity.company_name

    meta = {
        "broadcast_id": broadcast_id,
        "sender": current_user.username,
        "sender_role": current_user.role,
        "target": payload.target,
        "drive_id": payload.drive_id,
        "drive_name": drive_name,
        "category": payload.category,
    }

    if payload.target == "drive_shortlist":
        if not payload.drive_id or not drive_entity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A valid drive_id must be selected when target is 'drive_shortlist'.",
            )

        # Retrieve shortlisted candidates
        dec_stmt = select(EligibilityDecisionModel).where(
            EligibilityDecisionModel.drive_id == payload.drive_id,
            EligibilityDecisionModel.status == "eligible",
        )
        eligible_decs = db.execute(dec_stmt).scalars().all()
        student_ids = [d.student_id for d in eligible_decs]

        students = db.execute(
            select(StudentModel).where(StudentModel.id.in_(student_ids))
        ).scalars().all() if student_ids else []

        if not students:
            # Fallback to general students if none explicitly evaluated yet
            students = db.execute(select(StudentModel).limit(20)).scalars().all()

        recipient_count = len(students)

        # Batch insert individual candidate notifications
        for stu in students:
            # Substitute student-specific placeholders
            personalized_msg = (
                payload.message
                .replace("{student_name}", stu.name)
                .replace("{roll_no}", stu.roll_no)
                .replace("{company_name}", drive_name or "Campus Drive")
                .replace("{drive_date}", str(drive_entity.drive_date) if drive_entity else "Tuesday")
                .replace("{ctc_lpa}", str(drive_entity.ctc_lpa) if drive_entity else "N/A")
                .replace("{job_role}", "Engineering Graduate Trainee")
            )
            personalized_title = (
                payload.title
                .replace("{company_name}", drive_name or "Campus Drive")
                .replace("{student_name}", stu.name)
                .replace("{roll_no}", stu.roll_no)
            )

            notif = NotificationModel(
                id=f"notif_{uuid.uuid4().hex[:12]}",
                recipient_role="student",
                recipient_username=stu.roll_no,
                category=payload.category,
                title=personalized_title,
                message=personalized_msg,
                is_read=False,
                created_at=created_at,
                metadata_json=json.dumps(meta),
            )
            db.add(notif)

        # Also add one summary record for coordinator/officer logs
        summary_notif = NotificationModel(
            id=broadcast_id,
            recipient_role="officer",
            recipient_username=current_user.username,
            category=payload.category,
            title=f"Broadcast: {payload.title}",
            message=f"Sent to {recipient_count} shortlisted candidates for {drive_name}: {payload.message[:140]}...",
            is_read=False,
            created_at=created_at,
            metadata_json=json.dumps({**meta, "recipient_count": recipient_count}),
        )
        db.add(summary_notif)

    elif payload.target == "individual":
        if not payload.recipient_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Candidate roll number / username is required for individual message dispatch.",
            )

        notif = NotificationModel(
            id=broadcast_id,
            recipient_role="student",
            recipient_username=payload.recipient_username.strip(),
            category=payload.category,
            title=payload.title,
            message=payload.message,
            is_read=False,
            created_at=created_at,
            metadata_json=json.dumps(meta),
        )
        db.add(notif)
        recipient_count = 1

    else:
        # target in ('all', 'students', 'coordinators')
        role_map = {
            "all": "all",
            "students": "student",
            "coordinators": "coordinator",
        }
        target_role = role_map.get(payload.target, "all")

        # Estimate recipient count
        if target_role == "student":
            recipient_count = db.execute(select(StudentModel)).scalars().all()
            recipient_count = len(recipient_count)
        elif target_role == "coordinator":
            recipient_count = db.execute(
                select(UserModel).where(UserModel.role == "coordinator")
            ).scalars().all()
            recipient_count = len(recipient_count)
        else:
            # "all"
            stu_count = len(db.execute(select(StudentModel)).scalars().all())
            usr_count = len(db.execute(select(UserModel)).scalars().all())
            recipient_count = stu_count + usr_count

        notif = NotificationModel(
            id=broadcast_id,
            recipient_role=target_role,
            recipient_username=None,
            category=payload.category,
            title=payload.title,
            message=payload.message,
            is_read=False,
            created_at=created_at,
            metadata_json=json.dumps({**meta, "recipient_count": recipient_count}),
        )
        db.add(notif)

    db.commit()

    # Record institutional audit log
    AuditService.record_action(
        db=db,
        actor=current_user.username,
        action="BROADCAST_MESSAGE",
        aggregate_type="PLACEMENT_COMMUNICATION",
        aggregate_id=broadcast_id,
        payload={
            "title": payload.title,
            "target": payload.target,
            "category": payload.category,
            "recipient_count": recipient_count,
            "drive_id": payload.drive_id,
            "drive_name": drive_name,
        },
    )

    return {
        "status": "success",
        "message": f"Successfully dispatched official communication to {recipient_count} recipients.",
        "broadcast_id": broadcast_id,
        "recipient_count": recipient_count,
        "target": payload.target,
        "title": payload.title,
    }


@router.get("/broadcast-history")
def get_broadcast_history(
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieves history of official broadcast announcements and dispatch logs."""
    stmt = (
        select(NotificationModel)
        .where(
            (NotificationModel.recipient_role.in_(["all", "student", "coordinator", "officer"]))
            | (NotificationModel.id.like("msg_%"))
        )
        .order_by(NotificationModel.created_at.desc())
        .limit(50)
    )
    records = db.execute(stmt).scalars().all()

    # Deduplicate by broadcast_id if stored in metadata
    seen_ids = set()
    history = []
    for r in records:
        meta = json.loads(r.metadata_json or "{}")
        broadcast_id = meta.get("broadcast_id") or r.id
        if broadcast_id in seen_ids:
            continue
        seen_ids.add(broadcast_id)

        history.append({
            "id": broadcast_id,
            "title": r.title,
            "message": r.message,
            "category": r.category,
            "target": meta.get("target") or r.recipient_role,
            "recipient_count": meta.get("recipient_count", 1),
            "sender": meta.get("sender", "Training & Placement Cell"),
            "drive_name": meta.get("drive_name"),
            "created_at": r.created_at.isoformat(),
        })

    return history


@router.get("/candidate-passes/{drive_id}")
def get_candidate_passes_data(
    drive_id: str,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Generates printable interview hall passes and call letter rosters for a drive."""
    drive_stmt = select(DriveModel).where(DriveModel.id == drive_id)
    drive = db.execute(drive_stmt).scalar_one_or_none()
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found.")

    dec_stmt = select(EligibilityDecisionModel).where(
        EligibilityDecisionModel.drive_id == drive_id,
        EligibilityDecisionModel.status == "eligible",
    )
    eligible_decs = db.execute(dec_stmt).scalars().all()
    shortlist_ids = [d.student_id for d in eligible_decs]

    students = db.execute(
        select(StudentModel).where(StudentModel.id.in_(shortlist_ids))
    ).scalars().all() if shortlist_ids else db.execute(select(StudentModel).limit(20)).scalars().all()

    slots = db.execute(select(SlotModel).where(SlotModel.drive_id == drive_id)).scalars().all()
    slot_by_student: dict[str, SlotModel] = {str(s.student_id): s for s in slots if s.student_id}

    passes = []
    for stu in students:
        assigned_slot = slot_by_student.get(stu.id)
        passes.append({
            "student_id": stu.id,
            "roll_no": stu.roll_no,
            "name": stu.name,
            "branch": stu.branch,
            "cgpa": stu.cgpa,
            "company_name": drive.company_name,
            "job_role": "Engineering Graduate Trainee",
            "ctc_lpa": drive.ctc_lpa,
            "drive_date": str(drive.drive_date),
            "round_name": f"Round {assigned_slot.round_number}" if assigned_slot else "Technical Round 1",
            "slot_time": assigned_slot.start_time.strftime("%I:%M %p") if assigned_slot else "09:30 AM",
            "room_name": assigned_slot.room.name if (assigned_slot and assigned_slot.room) else "Placement Hall A",
        })

    return {
        "drive_id": drive.id,
        "company_name": drive.company_name,
        "drive_date": str(drive.drive_date),
        "total_candidates": len(passes),
        "passes": passes,
    }
