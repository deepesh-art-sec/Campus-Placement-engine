"""
Company Export Mapping and Header Auto-Detection Engine.
Analyzes company sample sheets (XLSX / CSV) and determines exact column layout.
"""

from __future__ import annotations

import csv
import io
import re

import openpyxl
from pydantic import BaseModel, ConfigDict, Field

CANONICAL_FIELDS = {
    "roll_no": "Student Roll Number",
    "name": "Candidate Full Name",
    "email": "Email Address",
    "branch": "Academic Branch / Department",
    "cgpa": "Cumulative Grade Point Average (CGPA)",
    "tenth_percentage": "10th Percentage",
    "twelfth_percentage": "12th Percentage",
    "round_name": "Scheduled Assessment / Interview Round",
    "slot_time": "Scheduled Slot Time",
    "room_name": "Venue / Room Name",
    "panel_name": "Assigned Panel",
}

HEADER_GUESS_PATTERNS: dict[str, list[str]] = {
    "roll_no": [r"roll", r"reg", r"usn", r"candidate\s*id", r"student\s*id", r"enrollment"],
    "name": [r"candidate\s*name", r"student\s*name", r"full\s*name", r"name"],
    "email": [r"email", r"mail", r"e-mail"],
    "branch": [r"branch", r"dept", r"department", r"stream", r"discipline", r"course"],
    "cgpa": [r"cgpa", r"gpa", r"aggregate", r"b\.?tech\s*%", r"degree\s*%"],
    "tenth_percentage": [r"10th", r"tenth", r"ssc", r"matric"],
    "twelfth_percentage": [r"12th", r"twelfth", r"hsc", r"inter"],
    "round_name": [r"round", r"assessment", r"interview\s*type"],
    "slot_time": [r"slot", r"time", r"schedule", r"timing"],
    "room_name": [r"venue", r"room", r"cabin", r"hall", r"location"],
    "panel_name": [r"panel", r"interviewer", r"board"],
}


class CompanyExportMapping(BaseModel):
    """Specification of exact company sheet formatting and header mapping."""
    model_config = ConfigDict(frozen=True)

    company_id: str
    company_name: str
    sheet_name: str = "Candidates"
    date_format: str = "YYYY-MM-DD"
    column_order: list[str] = Field(default_factory=list)
    canonical_mapping: dict[str, str] = Field(default_factory=dict)  # target_header -> canonical_field
    column_widths: dict[str, float] = Field(default_factory=dict)


def guess_canonical_field(header_text: str) -> str | None:
    """Auto-detects the matching canonical field for a raw company header string."""
    norm = header_text.strip().lower()
    for field_key, patterns in HEADER_GUESS_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, norm):
                return field_key
    return None


def parse_sample_file(
    file_bytes: bytes,
    filename: str,
    company_id: str,
    company_name: str,
) -> CompanyExportMapping:
    """Parses an uploaded sample XLSX or CSV file to extract headers, sheet name, and column widths."""
    headers: list[str] = []
    sheet_name = "Candidates"
    widths: dict[str, float] = {}

    if filename.lower().endswith(".xlsx"):
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        ws = wb.active
        sheet_name = ws.title if ws else "Candidates"

        if ws:
            first_row = [cell.value for cell in next(ws.iter_rows(max_row=1), [])]
            headers = [str(val).strip() for val in first_row if val is not None]

            for col_letter, col_dimension in ws.column_dimensions.items():
                if col_dimension.width:
                    col_idx = openpyxl.utils.column_index_from_string(col_letter) - 1
                    if 0 <= col_idx < len(headers):
                        widths[headers[col_idx]] = float(col_dimension.width)
    else:
        # CSV parsing
        text_content = file_bytes.decode("utf-8-sig", errors="replace")
        reader = csv.reader(io.StringIO(text_content))
        for row in reader:
            if row:
                headers = [h.strip() for h in row if h.strip()]
                break

    mapping: dict[str, str] = {}
    for h in headers:
        guessed = guess_canonical_field(h)
        if guessed:
            mapping[h] = guessed

    return CompanyExportMapping(
        company_id=company_id,
        company_name=company_name,
        sheet_name=sheet_name,
        date_format="YYYY-MM-DD",
        column_order=headers,
        canonical_mapping=mapping,
        column_widths=widths,
    )
