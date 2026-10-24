"""
Tests for Multi-Format Student Importer and Data Normalisation.
"""

import pytest

from backend.app.domain.exceptions import ProtectedAttributeViolationError
from backend.app.domain.models import RequirementSet
from backend.app.importers.student_importer import RowWarning, StudentImporter


@pytest.fixture
def importer() -> StudentImporter:
    return StudentImporter()


def test_normalise_percentage_fraction_and_symbol(importer: StudentImporter) -> None:
    warnings: list[RowWarning] = []
    # Decimal fraction 0.785 -> 78.5%
    val = importer.normalise_percentage(0.785, row_idx=1, roll_no="BT01", field_name="tenth_percentage", warnings=warnings)
    assert val == 78.5
    assert len(warnings) == 1
    assert "Interpreted fraction" in warnings[0].message

    # String with % sign "84.2%" -> 84.2
    val2 = importer.normalise_percentage("84.2%", row_idx=2, roll_no="BT02", field_name="twelfth_percentage", warnings=warnings)
    assert val2 == 84.2
    assert len(warnings) == 2
    assert "Stripped '%'" in warnings[1].message


def test_normalise_cgpa_four_point_scale(importer: StudentImporter) -> None:
    warnings: list[RowWarning] = []
    # 3.8 on 4.0 scale -> 9.5 on 10.0 scale
    val = importer.normalise_cgpa("3.8 / 4.0", row_idx=1, roll_no="BT01", warnings=warnings)
    assert val == 9.5
    assert len(warnings) == 1
    assert "Converted CGPA 3.8 on 4.0 scale to 9.5" in warnings[0].message


def test_normalise_branch_aliases(importer: StudentImporter) -> None:
    warnings: list[RowWarning] = []
    # CSE alias
    b1 = importer.normalise_branch("CSE", row_idx=1, roll_no="BT01", warnings=warnings)
    assert b1 == "Computer Science and Engineering"
    assert len(warnings) == 1
    assert "Mapped branch alias 'CSE'" in warnings[0].message

    # IT alias
    b2 = importer.normalise_branch("IT", row_idx=2, roll_no="BT02", warnings=warnings)
    assert b2 == "Information Technology"

    # Mech alias
    b3 = importer.normalise_branch("mech", row_idx=3, roll_no="BT03", warnings=warnings)
    assert b3 == "Mechanical Engineering"


def test_impossible_birth_date(importer: StudentImporter) -> None:
    warnings: list[RowWarning] = []
    # Future date
    with pytest.raises(ValueError, match="Impossible birth date"):
        importer.normalise_date_of_birth("2035-01-01", row_idx=1, roll_no="BT01", warnings=warnings)

    # 5-year-old child
    with pytest.raises(ValueError, match="calculated age"):
        importer.normalise_date_of_birth("2021-01-01", row_idx=1, roll_no="BT01", warnings=warnings)


def test_csv_import_with_messy_values_and_dry_run(importer: StudentImporter) -> None:
    csv_content = """roll_no,name,email,branch,cgpa,10th_percentage,12th_percentage,dob
BT101,John Doe,john@college.edu,CSE,3.6 / 4.0,0.85,78.5%,2003-05-15
BT102,Jane Smith,jane@college.edu,IT,8.4,0.92,90.0%,2003-08-20
BT103,Duplicate Roll,dup@college.edu,Mech,7.5,75.0,72.0%,2003-01-10
BT103,Duplicate Roll 2,dup2@college.edu,Mech,7.2,70.0,70.0%,2003-02-10
"""
    # Dry run
    report = importer.parse_file(csv_content, "test.csv", dry_run=True)
    assert report.is_dry_run is True
    assert report.total_rows == 4
    assert report.valid_rows == 3  # BT103 duplicate is rejected
    assert report.error_rows == 1
    assert any("Duplicate roll number" in err.message for err in report.errors)

    # Verify student 1 was converted properly
    s1 = report.imported_students[0]
    assert s1.roll_no == "BT101"
    assert s1.branch == "Computer Science and Engineering"
    assert s1.cgpa == 9.0  # 3.6 / 4.0 * 10
    assert s1.tenth_percentage == 85.0  # from 0.85 fraction
    assert s1.twelfth_percentage == 78.5


def test_protected_attribute_isolation() -> None:
    """Verifies that eligibility rules cannot target protected demographic attributes."""
    # Custom rule with valid criterion
    valid_req = RequirementSet(
        id="req-1",
        drive_id="d-1",
        min_cgpa=7.0,
        custom_rules={"min_credits": 120},
    )
    assert valid_req.min_cgpa == 7.0

    # Custom rule attempting to filter by protected attribute 'gender'
    with pytest.raises(ProtectedAttributeViolationError, match="protected demographic attribute"):
        RequirementSet(
            id="req-2",
            drive_id="d-1",
            min_cgpa=7.0,
            custom_rules={"gender": "female"},
        )

    # Custom rule attempting to filter by protected attribute 'caste'
    with pytest.raises(ProtectedAttributeViolationError, match="protected demographic attribute"):
        RequirementSet(
            id="req-3",
            drive_id="d-1",
            min_cgpa=7.0,
            custom_rules={"caste": "general"},
        )
