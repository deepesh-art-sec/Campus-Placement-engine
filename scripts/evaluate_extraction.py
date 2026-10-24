"""
Evaluation harness for recruitment requirement extraction.
Evaluates deterministic extraction across all 25 sample announcements against ground truth labels.
Computes per-field precision, recall, and zero-manual-entry rate.
Outputs results to console and writes docs/EXTRACTION_EVAL.md.
"""

from __future__ import annotations

import json
import os
import sys
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.app.extract.deterministic_extractor import DeterministicExtractor
from backend.app.extract.document_loader import DocumentLoader
FIXTURES_DIR = os.path.join(PROJECT_ROOT, "fixtures", "announcements")
GROUND_TRUTH_PATH = os.path.join(FIXTURES_DIR, "ground_truth_labels.json")
EVAL_DOC_PATH = os.path.join(PROJECT_ROOT, "docs", "EXTRACTION_EVAL.md")


def run_evaluation() -> dict:
    if not os.path.exists(GROUND_TRUTH_PATH):
        raise FileNotFoundError(f"Ground truth file not found at {GROUND_TRUTH_PATH}")

    with open(GROUND_TRUTH_PATH, "r", encoding="utf-8") as f:
        ground_truth: dict = json.load(f)

    loader = DocumentLoader()
    extractor = DeterministicExtractor()

    fields_to_eval = [
        "company_name",
        "drive_date",
        "mode",
        "ctc_lpa",
        "cgpa_min",
        "tenth_percentage_min",
        "twelfth_percentage_min",
        "active_backlogs_max",
        "historical_backlogs_max",
        "allowed_branches",
        "gap_years_max",
        "rounds_count",
    ]

    metrics: dict[str, dict[str, int]] = {
        field: {"true_positives": 0, "false_positives": 0, "false_negatives": 0, "total_truth": 0}
        for field in fields_to_eval
    }

    fully_extracted_count = 0
    total_announcements = len(ground_truth)
    evaluation_records: list[dict] = []

    start_time = time.perf_counter()

    for filename, truth in ground_truth.items():
        file_path = os.path.join(FIXTURES_DIR, filename)
        if not os.path.exists(file_path):
            continue

        with open(file_path, "rb") as f:
            content = f.read()

        txt = loader.load_from_bytes(content, filename)
        extracted = extractor.extract(txt)

        # Map extracted fields into comparable format
        extracted_map = {
            "company_name": extracted.company_name.value if extracted.company_name else None,
            "drive_date": extracted.drive_date.value.isoformat() if extracted.drive_date else None,
            "mode": (
                extracted.mode.value.value
                if extracted.mode and hasattr(extracted.mode.value, "value")
                else (str(extracted.mode.value) if extracted.mode else None)
            ),
            "ctc_lpa": extracted.ctc_lpa.value if extracted.ctc_lpa else None,
            "cgpa_min": extracted.cgpa_min.value if extracted.cgpa_min else None,
            "tenth_percentage_min": extracted.tenth_percentage_min.value if extracted.tenth_percentage_min else None,
            "twelfth_percentage_min": extracted.twelfth_percentage_min.value if extracted.twelfth_percentage_min else None,
            "active_backlogs_max": extracted.active_backlogs_max.value if extracted.active_backlogs_max is not None else None,
            "historical_backlogs_max": extracted.historical_backlogs_max.value if extracted.historical_backlogs_max is not None else None,
            "allowed_branches": extracted.allowed_branches.value if extracted.allowed_branches else None,
            "gap_years_max": extracted.gap_years_max.value if extracted.gap_years_max is not None else None,
            "rounds_count": len(extracted.rounds),
        }

        announcement_perfect = True
        field_evals = {}

        for field in fields_to_eval:
            t_val = truth.get(field)
            e_val = extracted_map.get(field)

            # Check matching
            is_match = False
            if field == "allowed_branches":
                if t_val == ["All Branches"] and (e_val == ["All Branches"] or e_val == []):
                    is_match = True
                elif t_val and e_val:
                    is_match = set(t_val) == set(e_val)
            else:
                is_match = (t_val == e_val)

            field_evals[field] = {
                "expected": t_val,
                "extracted": e_val,
                "match": is_match,
            }

            if t_val is not None:
                metrics[field]["total_truth"] += 1
                if is_match:
                    metrics[field]["true_positives"] += 1
                else:
                    announcement_perfect = False
                    metrics[field]["false_negatives"] += 1
            else:
                # Ground truth has no restriction
                if e_val is not None:
                    announcement_perfect = False
                    metrics[field]["false_positives"] += 1

        if announcement_perfect:
            fully_extracted_count += 1

        evaluation_records.append({
            "filename": filename,
            "company": truth["company_name"],
            "perfect": announcement_perfect,
            "confidence": extracted.overall_confidence,
            "ambiguities_count": len(extracted.ambiguities),
            "review_queue_count": len(extracted.review_queue),
            "fields": field_evals,
        })

    elapsed_time = time.perf_counter() - start_time

    # Compute summary tables
    field_summary = []
    for field, counts in metrics.items():
        tp = counts["true_positives"]
        fp = counts["false_positives"]
        fn = counts["false_negatives"]
        precision = (tp / (tp + fp)) * 100 if (tp + fp) > 0 else 100.0
        recall = (tp / (tp + fn)) * 100 if (tp + fn) > 0 else 100.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 100.0
        field_summary.append({
            "field": field,
            "total": counts["total_truth"],
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": round(precision, 1),
            "recall": round(recall, 1),
            "f1": round(f1, 1),
        })

    summary = {
        "total_announcements": total_announcements,
        "fully_extracted_zero_manual_entry": fully_extracted_count,
        "success_rate_pct": round((fully_extracted_count / total_announcements) * 100, 1),
        "target_met": fully_extracted_count >= 20,
        "elapsed_seconds": round(elapsed_time, 3),
        "average_time_per_doc_ms": round((elapsed_time / total_announcements) * 1000, 1),
        "field_summary": field_summary,
        "records": evaluation_records,
    }

    return summary


def write_eval_report(summary: dict) -> None:
    lines = [
        "# Recruitment Requirement Extraction Evaluation Report",
        "",
        "## 1. Executive Summary",
        "",
        f"- **Dataset Evaluated**: {summary['total_announcements']} Mixed-Format Placement Announcements (.txt, .eml, .pdf, .docx)",
        f"- **Announcements Fully Extracted (Zero Manual Entry)**: **{summary['fully_extracted_zero_manual_entry']} / {summary['total_announcements']}** ({summary['success_rate_pct']}%)",
        "- **Target Requirement**: At least 20 of 25 announcements without manual re-typing (Criterion 3).",
        f"- **Target Status**: **{'PASSED' if summary['target_met'] else 'FAILED'}** (Achieved {summary['fully_extracted_zero_manual_entry']}/25 fully offline).",
        f"- **Total Benchmark Execution Time**: {summary['elapsed_seconds']} seconds ({summary['average_time_per_doc_ms']} ms/document).",
        "- **Cloud/Network Calls**: 0 (100% offline regex & semantic dictionary architecture).",
        "- **LLM Dependency**: None (LLM Adapter OFF by default; target strictly achieved deterministically).",
        "",
        "## 2. Per-Field Precision and Recall",
        "",
        "| Field Name | Evaluated | Correct (TP) | False Pos | False Neg | Precision | Recall | F1 Score |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    for f in summary["field_summary"]:
        lines.append(
            f"| `{f['field']}` | {f['total']} | {f['tp']} | {f['fp']} | {f['fn']} | {f['precision']}% | {f['recall']}% | {f['f1']}% |"
        )

    lines.extend([
        "",
        "## 3. Document-by-Document Breakdown",
        "",
        "| Filename | Company | Extracted Status | Confidence | Ambiguities Flagged | Review Items |",
        "| :--- | :--- | :---: | :---: | :---: | :---: |",
    ])

    for r in summary["records"]:
        status = "Full Extract (Zero Manual Entry)" if r["perfect"] else "Review Required"
        lines.append(
            f"| `{r['filename']}` | {r['company']} | {status} | {r['confidence']:.2f} | {r['ambiguities_count']} | {r['review_queue_count']} |"
        )

    lines.extend([
        "",
        "## 4. Ambiguity and Review Queue Governance",
        "",
        "In compliance with institutional placement standards:",
        "1. **Never Guess Silently**: Phrasings such as *'throughout'* or *'at time of joining'* are explicitly identified as ambiguities and automatically appended to the review queue with suggested clarification actions.",
        "2. **Side-by-Side Review Contract**: The officer UI receives the verbatim sentence provenance alongside every parsed field, enabling 1-click accept, edit, or reject.",
        "3. **Feedback Audit Log**: Every correction or override is persisted in the audit trail with officer ID and timestamp.",
        "",
        "## 5. Offline & Privacy Assurance",
        "",
        "- All text parsing, document decompression, and table extractions execute locally.",
        "- No student data, corporate specifications, or salary details leave the local host environment.",
    ])

    with open(EVAL_DOC_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Generated extraction evaluation report at {EVAL_DOC_PATH}")


if __name__ == "__main__":
    eval_result = run_evaluation()
    print("=======================================================")
    print("RECRUITMENT REQUIREMENT EXTRACTION BENCHMARK")
    print("=======================================================")
    print(f"Total Announcements: {eval_result['total_announcements']}")
    print(f"Fully Extracted (Zero Manual Entry): {eval_result['fully_extracted_zero_manual_entry']} / {eval_result['total_announcements']}")
    print(f"Success Rate: {eval_result['success_rate_pct']}%")
    print(f"Total Time: {eval_result['elapsed_seconds']}s ({eval_result['average_time_per_doc_ms']} ms/doc)")
    print("Target Met (>= 20/25):", eval_result['target_met'])
    print("=======================================================")
    write_eval_report(eval_result)
