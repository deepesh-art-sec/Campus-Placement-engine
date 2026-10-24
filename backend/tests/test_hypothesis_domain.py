"""
Property-based tests using Hypothesis for Placement Engine domain rules and transformations.
"""

from datetime import date

from hypothesis import given
from hypothesis import strategies as st

from backend.app.domain.models import BacklogRecord, BacklogStatus, Student
from backend.app.importers.student_importer import RowWarning, StudentImporter


@given(st.floats(min_value=0.01, max_value=1.0))
def test_fraction_percentage_normalisation_property(frac: float) -> None:
    importer = StudentImporter()
    warnings: list[RowWarning] = []
    normalised = importer.normalise_percentage(frac, 1, "TEST01", "tenth_percentage", warnings)
    assert normalised is not None
    assert 1.0 <= normalised <= 100.0
    assert len(warnings) == 1


@given(st.floats(min_value=0.0, max_value=4.0))
def test_four_point_scale_cgpa_property(gpa: float) -> None:
    importer = StudentImporter()
    warnings: list[RowWarning] = []
    raw_str = f"{gpa:.2f} / 4.0"
    normalised = importer.normalise_cgpa(raw_str, 1, "TEST01", warnings)
    assert 0.0 <= normalised <= 10.0


@given(
    active_count=st.integers(min_value=0, max_value=5),
    cleared_count=st.integers(min_value=0, max_value=5),
)
def test_backlog_counts_invariant(active_count: int, cleared_count: int) -> None:
    backlogs = []
    for i in range(active_count):
        backlogs.append(
            BacklogRecord(subject=f"Sub-Active-{i}", semester=1, status=BacklogStatus.ACTIVE)
        )
    for i in range(cleared_count):
        backlogs.append(
            BacklogRecord(
                subject=f"Sub-Cleared-{i}",
                semester=1,
                status=BacklogStatus.CLEARED,
                cleared_on=date(2025, 1, 1),
            )
        )

    student = Student(
        id="std-hyp",
        roll_no="HYP01",
        name="Test Invariant",
        email="hyp@college.edu",
        branch="Computer Science and Engineering",
        cgpa=8.0,
        tenth_percentage=80.0,
        date_of_birth=date(2003, 1, 1),
        backlogs=backlogs,
    )

    assert student.active_backlog_count() == active_count
    assert student.history_backlog_count() == active_count + cleared_count
    assert (student.active_backlog_count() > 0) == student.has_active_backlogs()
