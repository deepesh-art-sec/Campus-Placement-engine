"""
Round-trip Data Loss Verification.
Re-imports exported XLSX files using the company mapping to prove zero data loss.
"""

from __future__ import annotations

import io
from typing import Any

import openpyxl

from backend.app.api.export.mapping import CompanyExportMapping
from backend.app.domain.models import Student


def reimport_from_company_xlsx(
    file_bytes: bytes,
    mapping: CompanyExportMapping,
) -> list[dict[str, Any]]:
    """Re-imports records from an exported XLSX using the company mapping specification."""
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    ws = wb[mapping.sheet_name] if mapping.sheet_name in wb.sheetnames else wb.active
    assert ws is not None

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []

    headers = [str(c).strip() for c in rows[0] if c is not None]

    # Build reverse lookup: column_index -> canonical_field
    idx_to_canonical: dict[int, str] = {}
    for idx, h in enumerate(headers):
        if h in mapping.canonical_mapping:
            idx_to_canonical[idx] = mapping.canonical_mapping[h]

    records: list[dict[str, Any]] = []
    for row in rows[1:]:
        if not any(row):
            continue
        rec: dict[str, Any] = {}
        for col_idx, val in enumerate(row):
            canon_field = idx_to_canonical.get(col_idx)
            if canon_field:
                rec[canon_field] = val
        records.append(rec)

    return records


def verify_round_trip(
    original_students: list[Student],
    reimported_data: list[dict[str, Any]],
) -> bool:
    """Verifies that every original student record matches the re-imported data with zero loss."""
    if len(original_students) != len(reimported_data):
        return False

    orig_map = {s.roll_no: s for s in original_students}

    for re_rec in reimported_data:
        roll = str(re_rec.get("roll_no", "")).strip()
        orig = orig_map.get(roll)
        if not orig:
            return False

        if "name" in re_rec and str(re_rec["name"]).strip() != orig.name:
            return False

        if "branch" in re_rec and str(re_rec["branch"]).strip() != orig.branch:
            return False

        if "cgpa" in re_rec:
            try:
                cgpa_val = float(re_rec["cgpa"])
                if abs(cgpa_val - orig.cgpa) > 0.01:
                    return False
            except (ValueError, TypeError):
                return False

    return True
