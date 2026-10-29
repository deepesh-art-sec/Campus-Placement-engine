"""
Company-Format and Institutional Roster Export Routes.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.api.auth.dependencies import get_current_user, require_officer_or_coordinator
from backend.app.api.export.exporter import export_to_company_csv, export_to_company_xlsx
from backend.app.api.export.mapping import CompanyExportMapping, parse_sample_file
from backend.app.api.logging.audit_service import AuditService
from backend.app.api.reports.student_pdf import generate_student_status_pdf
from backend.app.domain.impact.output_queue import OutputQueueService
from backend.app.domain.models import Drive
from backend.app.scheduler.models import ScheduledItem
from backend.app.storage.database import get_db
from backend.app.storage.models.entities import (
    CompanyExportMappingModel,
    DriveModel,
    EligibilityDecisionModel,
    SlotModel,
    StudentModel,
    UserModel,
)
from backend.app.storage.repositories.mappers import student_entity_to_domain

router = APIRouter(prefix="/api/exports", tags=["Exports & Company Templates"])

_output_queue = OutputQueueService()


@router.post("/sample-mapping", response_model=CompanyExportMapping)
async def upload_sample_and_create_mapping(
    file: UploadFile = File(...),
    company_id: str = Form(...),
    company_name: str = Form(...),
    current_user: UserModel = Depends(require_officer_or_coordinator),
) -> CompanyExportMapping:
    """
    Parses a company's sample XLSX or CSV template once.
    Auto-detects matching canonical fields and column widths.
    """
    bytes_data = await file.read()
    mapping = parse_sample_file(
        file_bytes=bytes_data,
        filename=file.filename or "sample.xlsx",
        company_id=company_id,
        company_name=company_name,
    )
    return mapping


@router.get("/company-mappings")
def list_company_mappings(
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Lists officer-saved company export layouts for coordinator review and export generation."""
    entities = db.execute(select(CompanyExportMappingModel)).scalars().all()
    return [
        {
            "id": e.id,
            "company_id": e.company_id,
            "company_name": e.company_name,
            "sheet_name": e.sheet_name,
            "date_format": e.date_format,
            "column_order": json.loads(e.column_mappings_json or "{}").get("order", []),
            "column_widths": json.loads(e.column_widths_json or "{}"),
        }
        for e in entities
    ]


@router.post("/company-mapping/save")
def save_company_mapping(
    mapping: CompanyExportMapping,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Persists an approved company mapping layout with manual overrides."""
    stmt = select(CompanyExportMappingModel).where(CompanyExportMappingModel.company_id == mapping.company_id)
    entity = db.execute(stmt).scalar_one_or_none()

    if entity:
        entity.company_name = mapping.company_name
        entity.sheet_name = mapping.sheet_name
        entity.date_format = mapping.date_format
        entity.column_mappings_json = json.dumps({
            "order": mapping.column_order,
            "mapping": mapping.canonical_mapping,
        })
        entity.column_widths_json = json.dumps(mapping.column_widths)
    else:
        entity = CompanyExportMappingModel(
            id=f"map_{mapping.company_id}",
            company_id=mapping.company_id,
            company_name=mapping.company_name,
            sheet_name=mapping.sheet_name,
            date_format=mapping.date_format,
            column_mappings_json=json.dumps({
                "order": mapping.column_order,
                "mapping": mapping.canonical_mapping,
            }),
            column_widths_json=json.dumps(mapping.column_widths),
        )
        db.add(entity)

    db.commit()
    return {"message": f"Mapping for '{mapping.company_name}' successfully saved."}


@router.api_route("/company-format/{drive_id}", methods=["GET", "POST"])
@router.api_route("/company/{drive_id}", methods=["GET", "POST"])
@router.api_route("/shortlist/{drive_id}", methods=["GET", "POST"])
def export_company_format(
    drive_id: str,
    as_csv: bool = False,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> Response:
    """Exports candidate shortlist and schedule in exact company template format."""
    stmt_drv = select(DriveModel).where(DriveModel.id == drive_id)
    drive_entity = db.execute(stmt_drv).scalar_one_or_none()
    if not drive_entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drive not found.")

    # Fetch mapping
    stmt_map = select(CompanyExportMappingModel).where(CompanyExportMappingModel.company_id == drive_entity.company_id)
    map_entity = db.execute(stmt_map).scalar_one_or_none()

    if map_entity:
        col_data = json.loads(map_entity.column_mappings_json)
        mapping = CompanyExportMapping(
            company_id=map_entity.company_id,
            company_name=map_entity.company_name,
            sheet_name=map_entity.sheet_name,
            date_format=map_entity.date_format,
            column_order=col_data.get("order", []),
            canonical_mapping=col_data.get("mapping", {}),
            column_widths=json.loads(map_entity.column_widths_json),
        )
    else:
        # Default institutional layout
        mapping = CompanyExportMapping(
            company_id=drive_entity.company_id,
            company_name=drive_entity.company_name,
            sheet_name="Candidates",
            column_order=["Roll Number", "Candidate Name", "Email Address", "Branch", "CGPA", "Round", "Slot Time", "Venue"],
            canonical_mapping={
                "Roll Number": "roll_no",
                "Candidate Name": "name",
                "Email Address": "email",
                "Branch": "branch",
                "CGPA": "cgpa",
                "Round": "round_name",
                "Slot Time": "slot_time",
                "Venue": "room_name",
            },
        )

    # Fetch eligible students
    dec_stmt = select(EligibilityDecisionModel).where(
        EligibilityDecisionModel.drive_id == drive_id,
        EligibilityDecisionModel.status == "eligible",
    )
    eligible_decisions = db.execute(dec_stmt).scalars().all()
    shortlist_ids = [d.student_id for d in eligible_decisions]

    student_entities = db.execute(
        select(StudentModel).where(StudentModel.id.in_(shortlist_ids))
    ).scalars().all() if shortlist_ids else db.execute(select(StudentModel).limit(10)).scalars().all()

    students = [student_entity_to_domain(s) for s in student_entities]

    # Fetch slots
    slots = db.execute(select(SlotModel).where(SlotModel.drive_id == drive_id)).scalars().all()
    scheduled_items = [
        ScheduledItem(
            schedule_id="sch_1",
            drive_id=drive_id,
            round_number=s.round_number,
            round_name=f"Round {s.round_number}",
            student_ids=[str(s.student_id)],
            room_id=s.room_id or "r1",
            room_name=s.room.name if s.room else "Venue",
            start_time=s.start_time,
            end_time=s.end_time,
        )
        for s in slots
    ]

    # Audit log the export
    AuditService.record_export(
        db=db,
        actor=current_user.username,
        export_type="COMPANY_CUSTOM_XLSX" if not as_csv else "COMPANY_CUSTOM_CSV",
        company_id=drive_entity.company_id,
        candidate_count=len(students),
    )

    clean_comp = drive_entity.company_name.replace(" ", "_")
    if as_csv:
        csv_text = export_to_company_csv(students, scheduled_items, mapping)
        return Response(
            content=csv_text,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={clean_comp}_shortlist.csv"},
        )

    xlsx_bytes = export_to_company_xlsx(students, scheduled_items, mapping)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={clean_comp}_shortlist.xlsx"},
    )


@router.get("/recruiter-roster/{drive_id}")
def export_recruiter_roster(
    drive_id: str,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Generates standard recruiter roster export with clipboard text."""
    stmt_drv = select(DriveModel).where(DriveModel.id == drive_id)
    drive_entity = db.execute(stmt_drv).scalar_one_or_none()
    if not drive_entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drive not found.")

    students = [student_entity_to_domain(s) for s in db.execute(select(StudentModel).limit(30)).scalars().all()]
    slots = db.execute(select(SlotModel).where(SlotModel.drive_id == drive_id)).scalars().all()
    scheduled_items = [
        ScheduledItem(
            schedule_id="sch_1",
            drive_id=drive_id,
            round_number=s.round_number,
            round_name=f"Round {s.round_number}",
            student_ids=[str(s.student_id)],
            room_id=s.room_id or "r1",
            room_name=s.room.name if s.room else "Venue",
            start_time=s.start_time,
            end_time=s.end_time,
        )
        for s in slots
    ]

    drive_domain = Drive(
        id=drive_entity.id,
        company_id=drive_entity.company_id,
        company_name=drive_entity.company_name,
        drive_date=drive_entity.drive_date,
        ctc_lpa=drive_entity.ctc_lpa,
    )

    roster = _output_queue.generate_recruiter_export(
        drive=drive_domain,
        students=students,
        schedule_items=scheduled_items,
    )

    AuditService.record_export(
        db=db,
        actor=current_user.username,
        export_type="RECRUITER_ROSTER",
        company_id=drive_entity.company_id,
        candidate_count=roster.total_candidates,
    )

    return roster.model_dump()


@router.get("/student-pdf/{student_id}")
def export_student_pdf(
    student_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Generates and downloads student status sheet PDF (Staff or candidate accessing self)."""
    if current_user.role == "student" and current_user.student_id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You can only generate your own status sheet.",
        )

    stmt = select(StudentModel).where(StudentModel.id == student_id)
    student_entity = db.execute(stmt).scalar_one_or_none()
    if not student_entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    domain_stu = student_entity_to_domain(student_entity)
    pdf_bytes = generate_student_status_pdf(
        student=domain_stu,
        drive_decisions=[],
        scheduled_slots=[],
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


# -----------------------------------------------------------------------------
# Alias Router for /api/export (Singular) Prefix
# -----------------------------------------------------------------------------
export_alias_router = APIRouter(prefix="/api/export", tags=["Exports & Company Templates"])


@export_alias_router.api_route("/company-format/{drive_id}", methods=["GET", "POST"])
@export_alias_router.api_route("/company/{drive_id}", methods=["GET", "POST"])
@export_alias_router.api_route("/shortlist/{drive_id}", methods=["GET", "POST"])
def export_company_alias(
    drive_id: str,
    as_csv: bool = False,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> Response:
    """Alias for company format export supporting /api/export prefix."""
    return export_company_format(drive_id=drive_id, as_csv=as_csv, current_user=current_user, db=db)
