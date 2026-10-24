"""
Student Registry Management & Privacy-Guaranteed Student Portal.
Strictly ensures students can only ever access their own placement records.
"""

from __future__ import annotations

import datetime
import json
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.auth.dependencies import (
    get_current_user,
    require_officer,
    require_officer_or_coordinator,
    require_student,
)
from backend.app.api.logging.audit_service import AuditService
from backend.app.api.reports.student_pdf import generate_student_status_pdf
from backend.app.domain.eligibility.ast import RuleSet
from backend.app.domain.eligibility.evaluator import EligibilityEvaluator, EligibilityStatus
from backend.app.domain.models import (
    Drive,
    ProtectedDemographics,
    Student,
)
from backend.app.domain.policy.catalog import STRICT_ONE_OFFER_POLICY
from backend.app.domain.policy.checker import policy_check
from backend.app.domain.policy.models import PolicyCheckStatus
from backend.app.importers.student_importer import StudentImporter
from backend.app.storage.database import get_db
from backend.app.storage.models.entities import (
    DriveModel,
    EligibilityDecisionModel,
    SlotModel,
    StudentModel,
    UserModel,
)
from backend.app.storage.repositories.mappers import (
    student_domain_to_entity,
    student_entity_to_domain,
)

router = APIRouter(tags=["Students & Portal"])


class StudentCreateUpdateRequest(BaseModel):
    roll_no: str
    name: str
    email: str
    branch: str
    program: str = "B.Tech"
    cgpa: float = Field(ge=0.0, le=10.0)
    tenth_percentage: float = Field(ge=0.0, le=100.0)
    twelfth_percentage: float | None = Field(default=None, ge=0.0, le=100.0)
    diploma_percentage: float | None = Field(default=None, ge=0.0, le=100.0)
    date_of_birth: datetime.date
    # Protected demographics (optional, never used in eligibility)
    gender: str | None = None
    caste: str | None = None
    religion: str | None = None
    category: str | None = None


# -----------------------------------------------------------------------------
# 1. Officer & Coordinator Endpoints
# -----------------------------------------------------------------------------

@router.get("/api/students")
def list_students(
    branch: str | None = None,
    limit: int = Query(default=2000, ge=1, le=3000),
    offset: int = Query(default=0, ge=0),
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Lists students with optional branch filtering (Staff only)."""
    stmt = select(StudentModel)
    if branch:
        stmt = stmt.where(StudentModel.branch == branch)
    stmt = stmt.offset(offset).limit(limit)

    results = db.execute(stmt).scalars().all()
    count_stmt = select(StudentModel)
    if branch:
        count_stmt = count_stmt.where(StudentModel.branch == branch)
    total_count = len(db.execute(count_stmt).scalars().all())

    return {
        "total": total_count,
        "offset": offset,
        "limit": limit,
        "items": [
            {
                "id": s.id,
                "roll_no": s.roll_no,
                "name": s.name,
                "email": s.email,
                "branch": s.branch,
                "program": s.program,
                "cgpa": s.cgpa,
                "tenth_percentage": s.tenth_percentage,
                "twelfth_percentage": s.twelfth_percentage,
                "date_of_birth": s.date_of_birth.isoformat(),
                "active_backlogs": len([b for b in s.backlogs if b.status == "active"]),
                "history_backlogs": len([b for b in s.backlogs if b.status == "cleared"]),
                "existing_offers_count": len(s.offers),
            }
            for s in results
        ],
    }


@router.get("/api/students/{student_id}")
def get_student(
    student_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Retrieves full details of a student.
    Enforces strict server-side authorization: Students can ONLY view their own ID!
    """
    # Privacy verification: prevent ID tampering
    if current_user.role == "student" and current_user.student_id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Candidates are strictly restricted from inspecting other students' records.",
        )

    # Recruiter cannot browse student database directly
    if current_user.role == "recruiter_readonly":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied for recruiter accounts.",
        )

    stmt = select(StudentModel).where(StudentModel.id == student_id)
    student_entity = db.execute(stmt).scalar_one_or_none()
    if not student_entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    # Audit log access
    AuditService.record_student_access(
        db=db,
        actor=current_user.username,
        student_id=student_id,
        action="VIEW_DETAILS",
        endpoint=f"/api/students/{student_id}",
    )

    domain_stu = student_entity_to_domain(student_entity)
    return domain_stu.model_dump()


@router.post("/api/students", status_code=status.HTTP_201_CREATED)
def create_student(
    req: StudentCreateUpdateRequest,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Creates a new student record (Staff only)."""
    import uuid

    demographics = None
    if any([req.gender, req.caste, req.religion, req.category]):
        demographics = ProtectedDemographics(
            gender=req.gender,
            caste=req.caste,
            religion=req.religion,
            category=req.category,
        )

    student = Student(
        id=str(uuid.uuid4()),
        roll_no=req.roll_no,
        name=req.name,
        email=req.email,
        branch=req.branch,
        program=req.program,
        cgpa=req.cgpa,
        tenth_percentage=req.tenth_percentage,
        twelfth_percentage=req.twelfth_percentage,
        diploma_percentage=req.diploma_percentage,
        date_of_birth=req.date_of_birth,
        protected_demographics=demographics,
    )
    entity = student_domain_to_entity(student)
    db.add(entity)
    db.commit()

    AuditService.record_student_access(
        db=db,
        actor=current_user.username,
        student_id=student.id,
        action="CREATE",
        details={"roll_no": student.roll_no},
    )
    return {"id": student.id, "message": "Student created successfully."}


@router.put("/api/students/{student_id}")
def update_student(
    student_id: str,
    req: StudentCreateUpdateRequest,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Updates academic details of a student (Staff only)."""
    stmt = select(StudentModel).where(StudentModel.id == student_id)
    student = db.execute(stmt).scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    student.name = req.name
    student.email = req.email
    student.branch = req.branch
    student.program = req.program
    student.cgpa = req.cgpa
    student.tenth_percentage = req.tenth_percentage
    student.twelfth_percentage = req.twelfth_percentage
    student.diploma_percentage = req.diploma_percentage
    student.date_of_birth = req.date_of_birth
    student.version += 1

    db.commit()

    AuditService.record_student_access(
        db=db,
        actor=current_user.username,
        student_id=student_id,
        action="UPDATE",
        details={"roll_no": req.roll_no},
    )
    return {"id": student_id, "message": "Student updated successfully."}


@router.delete("/api/students/{student_id}")
def delete_student(
    student_id: str,
    current_user: UserModel = Depends(require_officer),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Deletes a student record (Officer only)."""
    stmt = select(StudentModel).where(StudentModel.id == student_id)
    student = db.execute(stmt).scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    db.delete(student)
    db.commit()

    AuditService.record_student_access(
        db=db,
        actor=current_user.username,
        student_id=student_id,
        action="DELETE",
    )
    return {"message": "Student deleted successfully."}


@router.post("/api/students/import")
async def import_students(
    file: UploadFile = File(...),
    dry_run: bool = False,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Imports student roster from CSV or XLSX via Part 1 importer."""
    content = await file.read()
    importer = StudentImporter()
    report = importer.parse_file(file_content=content, filename=file.filename or "roster.csv", dry_run=dry_run)

    if not dry_run and len(report.imported_students) > 0:
        # Save imported students to DB with idempotent roll_no upsert
        existing_students = {st.roll_no: st.id for st in db.execute(select(StudentModel)).scalars().all()}
        for s in report.imported_students:
            if s.roll_no in existing_students:
                s.id = existing_students[s.roll_no]
            entity = student_domain_to_entity(s)
            db.merge(entity)
        db.commit()

    AuditService.record_export(
        db=db,
        actor=current_user.username,
        export_type="STUDENT_IMPORT",
        candidate_count=len(report.imported_students),
        metadata={"filename": file.filename, "dry_run": dry_run},
    )

    return {
        "filename": file.filename or "roster.csv",
        "total_rows": report.total_rows,
        "imported_count": len(report.imported_students),
        "error_rows": report.error_rows,
        "warning_count": report.warning_count,
        "errors": [e.model_dump() for e in report.errors],
    }


# -----------------------------------------------------------------------------
# 2. Student Self-Service Portal (Strictly Scoped)
# -----------------------------------------------------------------------------

@router.get("/api/portal/me")
def portal_get_me(
    current_user: UserModel = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Returns candidate's own academic and profile records."""
    assert current_user.student_id is not None
    stmt = select(StudentModel).where(StudentModel.id == current_user.student_id)
    student = db.execute(stmt).scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile record missing.")

    AuditService.record_student_access(
        db=db,
        actor=current_user.username,
        student_id=current_user.student_id,
        action="PORTAL_VIEW_PROFILE",
    )
    return student_entity_to_domain(student).model_dump()


@router.get("/api/portal/drives")
def portal_get_drives(
    current_user: UserModel = Depends(require_student),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    Returns candidate's eligibility across all published drives as
    a one-line plain-English explanation plus expandable detail.
    Never exposes rankings or other candidates' data.
    """
    assert current_user.student_id is not None
    stmt_stu = select(StudentModel).where(StudentModel.id == current_user.student_id)
    student_entity = db.execute(stmt_stu).scalar_one_or_none()
    if not student_entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student record not found.")

    student = student_entity_to_domain(student_entity)

    # Fetch all drives
    drives = db.execute(select(DriveModel)).scalars().all()
    results = []

    evaluator = EligibilityEvaluator()
    policy = STRICT_ONE_OFFER_POLICY

    for d in drives:
        # Check if saved eligibility decision exists
        dec_stmt = select(EligibilityDecisionModel).where(
            EligibilityDecisionModel.drive_id == d.id,
            EligibilityDecisionModel.student_id == student.id,
        )
        dec_entity = db.execute(dec_stmt).scalar_one_or_none()

        if dec_entity:
            reasons_list = json.loads(dec_entity.reasons_json) if dec_entity.reasons_json else []
            rule_ids = json.loads(dec_entity.rule_ids_json) if dec_entity.rule_ids_json else []
            headline = reasons_list[0] if reasons_list else f"Evaluated for {d.company_name}"
            results.append({
                "drive_id": d.id,
                "company_name": d.company_name,
                "ctc_lpa": d.ctc_lpa,
                "drive_date": d.drive_date.isoformat(),
                "status": dec_entity.status,
                "headline_reason": headline,
                "passed_rules": rule_ids,
                "failed_rules": [],
            })
        else:
            # Evaluate dynamically
            rule_set = RuleSet(id=f"dyn_{d.id}", name=f"{d.company_name} Rules", rules=[])
            academic_res = evaluator.evaluate(student, rule_set, drive_id=d.id)
            pol_res = policy_check(
                student=student,
                drive=Drive(
                    id=d.id,
                    company_id=d.company_id,
                    company_name=d.company_name,
                    drive_date=d.drive_date,
                    ctc_lpa=d.ctc_lpa,
                ),
                policy=policy,
            )

            is_eligible = (
                academic_res.status == EligibilityStatus.ELIGIBLE
                and pol_res.status == PolicyCheckStatus.ALLOWED
            )
            headline = academic_res.overall_student_reason or pol_res.plain_english_reason

            results.append({
                "drive_id": d.id,
                "company_name": d.company_name,
                "ctc_lpa": d.ctc_lpa,
                "drive_date": d.drive_date.isoformat(),
                "status": "eligible" if is_eligible else "ineligible",
                "headline_reason": headline,
                "passed_rules": [r.student_explanation for r in academic_res.passed_rules],
                "failed_rules": [r.student_explanation for r in academic_res.failed_rules],
            })

    return results


@router.get("/api/portal/schedule")
def portal_get_schedule(
    current_user: UserModel = Depends(require_student),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Returns candidate's own scheduled rounds and venues with clash alerts."""
    assert current_user.student_id is not None
    stmt = (
        select(SlotModel)
        .where(SlotModel.student_id == current_user.student_id)
        .order_by(SlotModel.start_time.asc())
    )
    slots = db.execute(stmt).scalars().all()

    # Detect clashes among candidate's own slots
    schedule_out = []

    for i in range(len(slots)):
        slot = slots[i]
        has_clash = False
        for j in range(len(slots)):
            if i != j:
                other = slots[j]
                if slot.start_time < other.end_time and slot.end_time > other.start_time:
                    has_clash = True

        schedule_out.append({
            "slot_id": slot.id,
            "drive_id": slot.drive_id,
            "round_name": f"Round {slot.round_number}",
            "room_name": slot.room.name if slot.room else "TBD",
            "building": slot.room.building if slot.room else "",
            "panel_name": slot.panel.name if slot.panel else "Panel A",
            "start_time": slot.start_time.strftime("%d-%b-%Y %H:%M"),
            "end_time": slot.end_time.strftime("%H:%M"),
            "has_clash": has_clash,
        })

    return schedule_out


@router.get("/api/portal/policy-status")
def portal_get_policy_status(
    current_user: UserModel = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Returns candidate's institutional offer policy status and upgrade rights."""
    assert current_user.student_id is not None
    stmt = select(StudentModel).where(StudentModel.id == current_user.student_id)
    student = db.execute(stmt).scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    domain_stu = student_entity_to_domain(student)
    policy = STRICT_ONE_OFFER_POLICY

    offers_count = len(domain_stu.existing_offers)
    max_offers = policy.max_total_offers
    can_sit_dream = policy.allow_upgrade_to_dream and offers_count < (max_offers + policy.max_dream_offers)

    return {
        "student_roll_no": domain_stu.roll_no,
        "policy_name": policy.name,
        "total_offers_secured": offers_count,
        "max_offers_allowed": max_offers,
        "is_locked_out": offers_count >= max_offers and not can_sit_dream,
        "can_participate_in_dream_drives": can_sit_dream,
        "dream_threshold_lpa": policy.dream_threshold_lpa,
        "plain_english_summary": policy.to_plain_english(),
    }


@router.get("/api/portal/status-sheet-pdf")
def download_status_sheet_pdf(
    current_user: UserModel = Depends(require_student),
    db: Session = Depends(get_db),
) -> Response:
    """Generates and downloads candidate's own placement status sheet in PDF."""
    assert current_user.student_id is not None
    stmt = select(StudentModel).where(StudentModel.id == current_user.student_id)
    student = db.execute(stmt).scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    domain_stu = student_entity_to_domain(student)

    # Dynamic evaluations
    drives_data = portal_get_drives(current_user=current_user, db=db)
    schedule_data = portal_get_schedule(current_user=current_user, db=db)

    pdf_bytes = generate_student_status_pdf(
        student=domain_stu,
        drive_decisions=drives_data,
        scheduled_slots=schedule_data,
    )

    AuditService.record_export(
        db=db,
        actor=current_user.username,
        export_type="STUDENT_STATUS_PDF",
        candidate_count=1,
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=placement_status_{domain_stu.roll_no}.pdf"},
    )
