"""
Local Offline Student Status Sheet PDF Generation Tests.
"""

from __future__ import annotations

import datetime

from backend.app.api.reports.student_pdf import generate_student_status_pdf
from backend.app.domain.models import (
    BacklogRecord,
    BacklogStatus,
    OfferRecord,
    OfferSource,
    OfferStatus,
    Student,
)


def test_student_pdf_generation_offline() -> None:
    student = Student(
        id="stu_pdf_01",
        roll_no="2026_CSE_888",
        name="Vikramaditya Rao",
        email="vikram@college.edu",
        branch="Computer Science and Engineering",
        program="B.Tech",
        cgpa=8.95,
        tenth_percentage=92.5,
        twelfth_percentage=91.0,
        date_of_birth=datetime.date(2004, 8, 20),
        backlogs=[BacklogRecord(subject="Engineering Physics", semester=1, status=BacklogStatus.ACTIVE)],
        existing_offers=[
            OfferRecord(
                company="TCS Digital",
                ctc_lpa=7.5,
                offer_date=datetime.date(2026, 9, 15),
                source=OfferSource.ON_CAMPUS,
                is_dream=False,
                status=OfferStatus.ACCEPTED,
            )
        ],
    )

    decisions = [
        {
            "company_name": "Google",
            "status": "eligible",
            "reason": "Satisfies CGPA cut-off >= 8.5 and 0 historical arrears.",
        },
        {
            "company_name": "Microsoft",
            "status": "ineligible",
            "reason": "Active backlogs (1) exceeds maximum permitted limit (0).",
        },
    ]

    slots = [
        {
            "round_name": "Technical Assessment 1",
            "start_time": "01-Nov-2026 09:30",
            "end_time": "11:00",
            "room_name": "Auditorium Hall A",
            "panel_name": "Panel 1",
        }
    ]

    pdf_bytes = generate_student_status_pdf(
        student=student,
        drive_decisions=decisions,
        scheduled_slots=slots,
        current_tier_label="Standard Offer Secured",
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    # Standard PDF magic header
    assert pdf_bytes.startswith(b"%PDF-")
