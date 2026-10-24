"""
Company-Format Export and Round-Trip Data Integrity Tests.
Verifies sample template auto-guessing, XLSX rendering, and lossless re-import.
"""

from __future__ import annotations

import datetime
import io

import openpyxl
import pytest

from backend.app.api.export.exporter import export_to_company_csv, export_to_company_xlsx
from backend.app.api.export.mapping import CompanyExportMapping, parse_sample_file
from backend.app.api.export.round_trip import reimport_from_company_xlsx, verify_round_trip
from backend.app.domain.models import Student
from backend.app.scheduler.models import ScheduledItem


@pytest.fixture
def sample_candidates() -> list[Student]:
    return [
        Student(
            id="stu_exp_01",
            roll_no="2026_CSE_101",
            name="Rahul Sharma",
            email="rahul@college.edu",
            branch="Computer Science",
            program="B.Tech",
            cgpa=8.75,
            tenth_percentage=91.0,
            twelfth_percentage=88.5,
            date_of_birth=datetime.date(2004, 3, 10),
        ),
        Student(
            id="stu_exp_02",
            roll_no="2026_IT_202",
            name="Pooja Patel",
            email="pooja@college.edu",
            branch="Information Technology",
            program="B.Tech",
            cgpa=9.15,
            tenth_percentage=94.0,
            twelfth_percentage=92.0,
            date_of_birth=datetime.date(2004, 7, 22),
        ),
    ]


@pytest.fixture
def company_sample_xlsx_bytes() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Campus_Recruitment_Roster"

    headers = ["Candidate ID", "Student Name", "Degree Discipline", "Graduation CGPA", "Assigned Venue"]
    ws.append(headers)

    # Set custom widths
    ws.column_dimensions["A"].width = 25.0
    ws.column_dimensions["B"].width = 30.0
    ws.column_dimensions["C"].width = 22.0
    ws.column_dimensions["D"].width = 18.0
    ws.column_dimensions["E"].width = 20.0

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def test_sample_file_header_parsing_and_auto_guess(company_sample_xlsx_bytes: bytes) -> None:
    mapping = parse_sample_file(
        file_bytes=company_sample_xlsx_bytes,
        filename="company_template.xlsx",
        company_id="comp_tech_corp",
        company_name="Tech Corp",
    )

    assert mapping.sheet_name == "Campus_Recruitment_Roster"
    assert mapping.column_order == ["Candidate ID", "Student Name", "Degree Discipline", "Graduation CGPA", "Assigned Venue"]
    assert mapping.canonical_mapping["Candidate ID"] == "roll_no"
    assert mapping.canonical_mapping["Student Name"] == "name"
    assert mapping.canonical_mapping["Degree Discipline"] == "branch"
    assert mapping.canonical_mapping["Graduation CGPA"] == "cgpa"
    assert mapping.canonical_mapping["Assigned Venue"] == "room_name"
    assert mapping.column_widths["Candidate ID"] == 25.0


def test_export_and_lossless_round_trip(
    sample_candidates: list[Student],
    company_sample_xlsx_bytes: bytes,
) -> None:
    # 1. Parse sample template
    mapping = parse_sample_file(
        file_bytes=company_sample_xlsx_bytes,
        filename="template.xlsx",
        company_id="comp_1",
        company_name="Google",
    )

    # 2. Export candidates using company specification
    slot_time = datetime.datetime(2026, 11, 1, 10, 0)
    sched_item = ScheduledItem(
        schedule_id="sch_test",
        drive_id="d1",
        round_number=1,
        round_name="Technical Interview",
        student_ids=["stu_exp_01", "stu_exp_02"],
        room_id="r101",
        room_name="Interview Room 3",
        start_time=slot_time,
        end_time=slot_time + datetime.timedelta(minutes=45),
    )

    exported_xlsx = export_to_company_xlsx(
        students=sample_candidates,
        schedule_items=[sched_item],
        mapping=mapping,
    )
    assert len(exported_xlsx) > 0

    # 3. Re-import from exported XLSX via company mapping
    reimported = reimport_from_company_xlsx(exported_xlsx, mapping)
    assert len(reimported) == 2

    # 4. Verify exact lossless fidelity
    is_lossless = verify_round_trip(sample_candidates, reimported)
    assert is_lossless is True

    # Check individual field mappings
    first = reimported[0]
    assert first["roll_no"] == "2026_CSE_101"
    assert first["name"] == "Rahul Sharma"
    assert first["branch"] == "Computer Science"
    assert abs(float(first["cgpa"]) - 8.75) < 0.001
    assert first["room_name"] == "Interview Room 3"


def test_export_to_csv_matches_header_order(sample_candidates: list[Student]) -> None:
    mapping = CompanyExportMapping(
        company_id="comp_2",
        company_name="Microsoft",
        sheet_name="Roster",
        column_order=["Roll No", "Full Name", "CGPA"],
        canonical_mapping={"Roll No": "roll_no", "Full Name": "name", "CGPA": "cgpa"},
    )
    csv_text = export_to_company_csv(sample_candidates, [], mapping)
    lines = csv_text.strip().split("\r\n") if "\r\n" in csv_text else csv_text.strip().split("\n")
    assert lines[0] == "Roll No,Full Name,CGPA"
    assert "2026_CSE_101,Rahul Sharma,8.75" in lines[1]
