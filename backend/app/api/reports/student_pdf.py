"""
Local Student Placement Status PDF Generator.
Builds an institutional placement status sheet 100% offline using ReportLab.
"""

from __future__ import annotations

import datetime
import io
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from backend.app.domain.models import Student


def generate_student_status_pdf(
    student: Student,
    drive_decisions: list[dict[str, Any]],
    scheduled_slots: list[dict[str, Any]],
    policy_name: str = "Standard Institutional Policy",
    current_tier_label: str = "No Active Offers",
) -> bytes:
    """Generates an institutional PDF report of the student's placement status and schedule."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1A365D"),
    )
    subtitle_style = ParagraphStyle(
        "DocSub",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#4A5568"),
    )
    section_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#2B6CB0"),
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#2D3748"),
    )
    bold_body = ParagraphStyle(
        "BoldBody",
        parent=body_style,
        fontName="Helvetica-Bold",
    )

    elements = []

    # 1. Header
    elements.append(Paragraph("OFFICE OF TRAINING AND PLACEMENT", title_style))
    elements.append(Paragraph(f"Official Placement Status Sheet — Generated {datetime.datetime.utcnow().strftime('%d %b %Y %H:%M UTC')}", subtitle_style))
    elements.append(Spacer(1, 12))

    # 2. Student Information Table
    backlog_count = len([b for b in student.backlogs if b.status.value == "active"])
    student_data = [
        [
            Paragraph("<b>Candidate Name:</b>", body_style),
            Paragraph(student.name, body_style),
            Paragraph("<b>Roll Number:</b>", body_style),
            Paragraph(student.roll_no, body_style),
        ],
        [
            Paragraph("<b>Branch / Dept:</b>", body_style),
            Paragraph(student.branch, body_style),
            Paragraph("<b>Cumulative CGPA:</b>", body_style),
            Paragraph(f"{student.cgpa:.2f}", body_style),
        ],
        [
            Paragraph("<b>10th Percentage:</b>", body_style),
            Paragraph(f"{student.tenth_percentage:.1f}%", body_style),
            Paragraph("<b>12th Percentage:</b>", body_style),
            Paragraph(f"{student.twelfth_percentage:.1f}%" if student.twelfth_percentage else "N/A", body_style),
        ],
        [
            Paragraph("<b>Active Backlogs:</b>", body_style),
            Paragraph(f"{backlog_count}", body_style),
            Paragraph("<b>Offer Policy Tier:</b>", body_style),
            Paragraph(current_tier_label, body_style),
        ],
    ]
    t_student = Table(student_data, colWidths=[110, 160, 110, 160])
    t_student.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    elements.append(t_student)
    elements.append(Spacer(1, 10))

    # 3. Existing Offers Section
    elements.append(Paragraph("Current Offers & Commitments", section_style))
    if student.existing_offers:
        offers_data = [[
            Paragraph("<b>Company</b>", bold_body),
            Paragraph("<b>Package (CTC)</b>", bold_body),
            Paragraph("<b>Date Offered</b>", bold_body),
            Paragraph("<b>Type</b>", bold_body),
            Paragraph("<b>Status</b>", bold_body),
        ]]
        for o in student.existing_offers:
            offers_data.append([
                Paragraph(o.company, body_style),
                Paragraph(f"{o.ctc_lpa:.1f} LPA", body_style),
                Paragraph(o.offer_date.strftime("%d-%b-%Y"), body_style),
                Paragraph("Dream" if o.is_dream else "Standard", body_style),
                Paragraph(o.status.value.upper(), body_style),
            ])
        t_offers = Table(offers_data, colWidths=[140, 100, 100, 100, 100])
        t_offers.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        elements.append(t_offers)
    else:
        elements.append(Paragraph("<i>No placement offers registered to date.</i>", body_style))

    elements.append(Spacer(1, 10))

    # 4. Drive Eligibility Summary
    elements.append(Paragraph("Drive Eligibility & Determination Rationale", section_style))
    if drive_decisions:
        dec_data = [[
            Paragraph("<b>Drive / Company</b>", bold_body),
            Paragraph("<b>Status</b>", bold_body),
            Paragraph("<b>Plain-English Rationale</b>", bold_body),
        ]]
        for d in drive_decisions:
            st = d.get("status", "ineligible").upper()
            status_color = "#276749" if st == "ELIGIBLE" else "#C53030"
            status_para = Paragraph(f"<font color='{status_color}'><b>{st}</b></font>", body_style)
            dec_data.append([
                Paragraph(d.get("company_name", "Unknown"), body_style),
                status_para,
                Paragraph(d.get("reason", "N/A"), body_style),
            ])
        t_dec = Table(dec_data, colWidths=[140, 90, 310])
        t_dec.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        elements.append(t_dec)
    else:
        elements.append(Paragraph("<i>No drives evaluated for this candidate.</i>", body_style))

    elements.append(Spacer(1, 10))

    # 5. Scheduled Assessment / Interview Slots
    elements.append(Paragraph("Upcoming Test & Interview Schedule", section_style))
    if scheduled_slots:
        sched_data = [[
            Paragraph("<b>Round</b>", bold_body),
            Paragraph("<b>Date & Slot Time</b>", bold_body),
            Paragraph("<b>Venue / Room</b>", bold_body),
            Paragraph("<b>Panel</b>", bold_body),
        ]]
        for s in scheduled_slots:
            sched_data.append([
                Paragraph(s.get("round_name", ""), body_style),
                Paragraph(f"{s.get('start_time', '')} - {s.get('end_time', '')}", body_style),
                Paragraph(s.get("room_name", ""), body_style),
                Paragraph(s.get("panel_name", "N/A"), body_style),
            ])
        t_sched = Table(sched_data, colWidths=[140, 160, 140, 100])
        t_sched.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        elements.append(t_sched)
    else:
        elements.append(Paragraph("<i>No interview or test slots scheduled currently.</i>", body_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
