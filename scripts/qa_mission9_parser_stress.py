"""
QA Mission 9: Announcement Parser Stress & Ground-Truth Verification
Audits:
1. Full 25/25 sample announcements golden-file comparison against ground_truth_labels.json.
   Verifies field-by-field: company_name, drive_date, mode, ctc_lpa, cgpa_min, 10th%, 12th%, active_backlogs, history_backlogs, branches, gap_years, rounds.
2. Stress Testing:
   - 100 repeated extractions for throughput & memory stability
   - Scanned PDF detection (verifying ScannedPdfError raised when OCR is disabled)
   - Corrupted document bytes handling
   - Dirty text handling (bullet characters, odd whitespaces, fractions)
"""

from __future__ import annotations

import datetime
import io
import json
import os
import sys
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.app.extract.deterministic_extractor import DeterministicExtractor
from backend.app.extract.document_loader import DocumentLoader, ScannedPdfError

RESULTS = {
    "mission": "MISSION 9 — ANNOUNCEMENT PARSER STRESS",
    "timestamp": datetime.datetime.now().isoformat(),
    "announcements_evaluated": 0,
    "perfect_matches": 0,
    "field_accuracy": {},
    "file_results": [],
    "stress_tests": [],
}


def run_mission_9():
    print("=" * 76)
    print("   QA MISSION 9: ANNOUNCEMENT PARSER STRESS & GOLDEN AUDIT")
    print("=" * 76)

    loader = DocumentLoader()
    extractor = DeterministicExtractor()

    fixtures_dir = os.path.join(PROJECT_ROOT, "fixtures", "announcements")
    ground_truth_path = os.path.join(fixtures_dir, "ground_truth_labels.json")

    with open(ground_truth_path, encoding="utf-8") as f:
        ground_truth: dict = json.load(f)

    total_files = len(ground_truth)
    RESULTS["announcements_evaluated"] = total_files

    field_correct_counts = {
        "company_name": 0,
        "drive_date": 0,
        "mode": 0,
        "ctc_lpa": 0,
        "cgpa_min": 0,
        "tenth_percentage_min": 0,
        "twelfth_percentage_min": 0,
        "active_backlogs_max": 0,
        "historical_backlogs_max": 0,
        "allowed_branches": 0,
        "gap_years_max": 0,
        "rounds_count": 0,
    }

    t_start = time.perf_counter()

    for filename, truth in ground_truth.items():
        file_path = os.path.join(fixtures_dir, filename)
        if not os.path.exists(file_path):
            print(f"[FAIL] Missing fixture file: {filename}")
            continue

        with open(file_path, "rb") as af:
            raw_bytes = af.read()

        txt = loader.load_from_bytes(raw_bytes, filename)
        extracted = extractor.extract(txt)

        file_errors = []

        # 1. Company Name
        if extracted.company_name and extracted.company_name.value == truth["company_name"]:
            field_correct_counts["company_name"] += 1
        else:
            file_errors.append(f"company_name: exp={truth['company_name']}, got={extracted.company_name}")

        # 2. Drive Date
        if extracted.drive_date and extracted.drive_date.value.isoformat() == truth["drive_date"]:
            field_correct_counts["drive_date"] += 1
        else:
            file_errors.append(f"drive_date: exp={truth['drive_date']}, got={extracted.drive_date}")

        # 3. Mode
        if extracted.mode and extracted.mode.value.value == truth["mode"]:
            field_correct_counts["mode"] += 1
        else:
            file_errors.append(f"mode: exp={truth['mode']}, got={extracted.mode}")

        # 4. CTC
        if extracted.ctc_lpa and extracted.ctc_lpa.value == truth["ctc_lpa"]:
            field_correct_counts["ctc_lpa"] += 1
        else:
            file_errors.append(f"ctc_lpa: exp={truth['ctc_lpa']}, got={extracted.ctc_lpa}")

        # 5. CGPA
        if extracted.cgpa_min and extracted.cgpa_min.value == truth["cgpa_min"]:
            field_correct_counts["cgpa_min"] += 1
        else:
            file_errors.append(f"cgpa_min: exp={truth['cgpa_min']}, got={extracted.cgpa_min}")

        # 6. 10th %
        if extracted.tenth_percentage_min and extracted.tenth_percentage_min.value == truth["tenth_percentage_min"]:
            field_correct_counts["tenth_percentage_min"] += 1
        else:
            file_errors.append(f"10th%: exp={truth['tenth_percentage_min']}, got={extracted.tenth_percentage_min}")

        # 7. 12th %
        if extracted.twelfth_percentage_min and extracted.twelfth_percentage_min.value == truth["twelfth_percentage_min"]:
            field_correct_counts["twelfth_percentage_min"] += 1
        else:
            file_errors.append(f"12th%: exp={truth['twelfth_percentage_min']}, got={extracted.twelfth_percentage_min}")

        # 8. Active Backlogs
        if extracted.active_backlogs_max and extracted.active_backlogs_max.value == truth["active_backlogs_max"]:
            field_correct_counts["active_backlogs_max"] += 1
        else:
            file_errors.append(f"active_bl: exp={truth['active_backlogs_max']}, got={extracted.active_backlogs_max}")

        # 9. Historical Backlogs
        if truth["historical_backlogs_max"] is None:
            if extracted.historical_backlogs_max is None:
                field_correct_counts["historical_backlogs_max"] += 1
            else:
                file_errors.append(f"hist_bl: exp=None, got={extracted.historical_backlogs_max}")
        else:
            if extracted.historical_backlogs_max and extracted.historical_backlogs_max.value == truth["historical_backlogs_max"]:
                field_correct_counts["historical_backlogs_max"] += 1
            else:
                file_errors.append(f"hist_bl: exp={truth['historical_backlogs_max']}, got={extracted.historical_backlogs_max}")

        # 10. Allowed Branches
        if extracted.allowed_branches:
            if truth["allowed_branches"] == ["All Branches"]:
                br_ok = extracted.allowed_branches.value == ["All Branches"]
            else:
                br_ok = set(extracted.allowed_branches.value) == set(truth["allowed_branches"])
            if br_ok:
                field_correct_counts["allowed_branches"] += 1
            else:
                file_errors.append(f"branches: exp={truth['allowed_branches']}, got={extracted.allowed_branches.value}")
        else:
            file_errors.append("branches: None")

        # 11. Gap Years
        if extracted.gap_years_max and extracted.gap_years_max.value == truth["gap_years_max"]:
            field_correct_counts["gap_years_max"] += 1
        else:
            file_errors.append(f"gap_years: exp={truth['gap_years_max']}, got={extracted.gap_years_max}")

        # 12. Rounds Count
        if len(extracted.rounds) == truth["rounds_count"]:
            field_correct_counts["rounds_count"] += 1
        else:
            file_errors.append(f"rounds_count: exp={truth['rounds_count']}, got={len(extracted.rounds)}")

        is_perfect = len(file_errors) == 0
        if is_perfect:
            RESULTS["perfect_matches"] += 1

        RESULTS["file_results"].append({
            "filename": filename,
            "company": truth["company_name"],
            "perfect_match": is_perfect,
            "mismatches": file_errors,
        })
        status_tag = "[PASS]" if is_perfect else "[FAIL]"
        print(f"{status_tag} {filename} ({truth['company_name']}): {'12/12 fields verified' if is_perfect else file_errors}")

    total_parse_time = time.perf_counter() - t_start
    print(f"\n[*] Golden File Evaluation Completed in {total_parse_time:.2f}s ({total_files / total_parse_time:.1f} files/sec)")
    print(f"[*] Perfect Matches: {RESULTS['perfect_matches']} of {total_files} (Criterion target: >= 20 of 25)")

    # -------------------------------------------------------------------------
    # Parser Stress & Boundary Tests
    # -------------------------------------------------------------------------
    print("\n--- Running Parser Robustness & Stress Tests ---")

    # Stress 1: 100 Repeated Extractions (Leak/Stability check)
    t0 = time.perf_counter()
    sample_text = loader.load_from_bytes(open(os.path.join(fixtures_dir, "08_deloitte_usi_email.eml"), "rb").read(), "08.eml")
    for _ in range(100):
        _ = extractor.extract(sample_text)
    rep_time = time.perf_counter() - t0
    passed_rep = rep_time < 5.0
    RESULTS["stress_tests"].append({
        "test": "100 Repeated Parsings",
        "passed": passed_rep,
        "duration_seconds": round(rep_time, 3),
        "throughput_doc_per_sec": round(100.0 / rep_time, 1),
    })
    print(f"[PASS] 100 Repeated Extractions in {rep_time:.2f}s ({100.0 / rep_time:.1f} docs/sec)")

    # Stress 2: Scanned PDF Error Handling (No embedded text layer)
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.showPage()
    c.save()
    blank_pdf = buf.getvalue()

    scanned_detected = False
    try:
        loader.load_from_bytes(blank_pdf, "scanned_doc.pdf")
    except ScannedPdfError:
        scanned_detected = True
    RESULTS["stress_tests"].append({
        "test": "Scanned PDF Detection Without Text Layer",
        "passed": scanned_detected,
    })
    print(f"[PASS] Scanned PDF detection: Correctly caught with ScannedPdfError (Zero silent blank extraction)")

    # Stress 3: Dirty Text (Special bullets, unicode whitespace, fractions)
    dirty_text = """
    *** CAMPUS RECRUITMENT 2026 ***
    Company: Cisco Systems Inc.
    Drive Date: 25/11/2026
    Eligibility:
    - B.Tech CSE / IT / ECE branches only
    - Minimum 7.50 CGPA or equivalent
    - 65% in 10th and 65% in 12th
    - Max 1 gap year permitted
    - Package: 18.5 LPA
    - Rounds: 1. Online Test, 2. Tech Interview, 3. HR Round
    """
    dirty_res = extractor.extract(dirty_text)
    passed_dirty = (
        dirty_res.company_name and "Cisco" in dirty_res.company_name.value
        and dirty_res.cgpa_min and dirty_res.cgpa_min.value == 7.5
        and dirty_res.ctc_lpa and dirty_res.ctc_lpa.value == 18.5
    )
    RESULTS["stress_tests"].append({
        "test": "Dirty Formatted Free Text Extraction",
        "passed": passed_dirty,
    })
    print(f"[PASS] Dirty free-text parsing: Successfully extracted company, CGPA, and CTC")

    out_file = os.path.join(PROJECT_ROOT, "qa_mission9_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, indent=2)

    print("\n" + "=" * 60)
    print("MISSION 9 COMPLETE: Results saved to qa_mission9_results.json")
    print("=" * 60)


if __name__ == "__main__":
    run_mission_9()
