"""
Comprehensive Accuracy & Benchmark Evaluator for IM-101 Announcement Extraction Feature.
Evaluates:
  - Field-level Precision, Recall, and F1 scores
  - Exact-Match Accuracy
  - Missing-Field Rate
  - Incorrect-Value Rate
  - End-to-End Document Accuracy
  - Separate reporting for Scanned PDFs vs Digital/Text documents vs Edge Cases
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from backend.app.extract.document_loader import (
    CorruptDocumentError,
    DocumentLoader,
    EmptyDocumentError,
    ScannedPdfError,
    UnsupportedFormatError,
)
from backend.app.extract.nlp_engine import NLPEngine
from backend.app.extract.patterns import parse_branches_string


def match_field(field_name: str, extracted_val: Any, expected_val: Any) -> bool:
    """Evaluates whether extracted field matches ground truth value."""
    if expected_val is None:
        return extracted_val is None

    if extracted_val is None:
        return False

    if field_name in ("cgpa_min", "tenth_percentage_min", "twelfth_percentage_min", "ctc_lpa", "ctc_min_lpa", "ctc_max_lpa"):
        try:
            return abs(float(extracted_val) - float(expected_val)) < 0.05
        except (ValueError, TypeError):
            return False

    if field_name in ("active_backlogs_max", "historical_backlogs_max", "rounds_count"):
        try:
            return int(extracted_val) == int(expected_val)
        except (ValueError, TypeError):
            return False

    if field_name == "allowed_branches":
        if isinstance(extracted_val, list) and isinstance(expected_val, list):
            # Normalize branch tokens for comparison
            ext_set = set([str(b).strip().upper() for b in extracted_val])
            exp_set = set([str(b).strip().upper() for b in expected_val])
            if "ALL BRANCHES" in exp_set:
                return "ALL BRANCHES" in ext_set or ext_set == exp_set
            intersection = ext_set.intersection(exp_set)
            union = ext_set.union(exp_set)
            return len(intersection) / len(union) >= 0.70 if union else True
        return False

    if field_name in ("drive_date", "application_deadline"):
        ext_str = str(extracted_val).split("T")[0].strip()
        exp_str = str(expected_val).split("T")[0].strip()
        return ext_str == exp_str

    if field_name in ("company_name", "role", "location"):
        s1 = str(extracted_val).strip().lower()
        s2 = str(expected_val).strip().lower()
        return s1 == s2 or s2 in s1 or s1 in s2

    return str(extracted_val).strip().lower() == str(expected_val).strip().lower()


def evaluate(dataset_dir: str | None = None) -> dict[str, Any]:
    if not dataset_dir:
        dataset_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "fixtures", "synthetic_100"))

    docs_dir = os.path.join(dataset_dir, "documents")
    gt_file = os.path.join(dataset_dir, "ground_truth.json")

    with open(gt_file, "r", encoding="utf-8") as f:
        ground_truth: dict[str, dict[str, Any]] = json.load(f)

    loader = DocumentLoader(ocr_enabled=True)
    engine = NLPEngine()

    fields_to_eval = [
        "company_name",
        "role",
        "allowed_branches",
        "cgpa_min",
        "tenth_percentage_min",
        "twelfth_percentage_min",
        "active_backlogs_max",
        "historical_backlogs_max",
        "ctc_lpa",
        "drive_date",
        "application_deadline",
    ]

    metrics: dict[str, dict[str, int]] = {
        f: {"tp": 0, "fp": 0, "fn": 0, "total_expected": 0, "total_extracted": 0, "mismatches": 0}
        for f in fields_to_eval
    }

    doc_results: list[dict[str, Any]] = []
    e2e_correct = 0
    scanned_correct = 0
    scanned_total = 0
    digital_correct = 0
    digital_total = 0
    edge_cases_handled = 0
    edge_cases_total = 0

    for filename, gt in ground_truth.items():
        doc_path = os.path.join(docs_dir, filename)
        is_error_case = gt.get("is_error_case", False)
        is_scanned = gt.get("document_format") == "scanned_pdf"

        if is_scanned:
            scanned_total += 1
        elif not is_error_case:
            digital_total += 1
        else:
            edge_cases_total += 1

        extracted_data: dict[str, Any] = {}
        error_raised = None

        try:
            with open(doc_path, "rb") as fp:
                file_bytes = fp.read()
            full_text, chunks, page_count = loader.load_structured(file_bytes, filename)
            extracted = engine.extract(full_text)

            extracted_data = {
                "company_name": extracted.company_name.value if extracted.company_name else None,
                "role": extracted.role.value if extracted.role else None,
                "location": extracted.location.value if extracted.location else None,
                "allowed_branches": extracted.allowed_branches.value if extracted.allowed_branches else None,
                "cgpa_min": extracted.cgpa_min.value if extracted.cgpa_min else None,
                "tenth_percentage_min": extracted.tenth_percentage_min.value if extracted.tenth_percentage_min else None,
                "twelfth_percentage_min": extracted.twelfth_percentage_min.value if extracted.twelfth_percentage_min else None,
                "active_backlogs_max": extracted.active_backlogs_max.value if extracted.active_backlogs_max is not None else None,
                "historical_backlogs_max": extracted.historical_backlogs_max.value if extracted.historical_backlogs_max is not None else None,
                "ctc_lpa": extracted.ctc_lpa.value if extracted.ctc_lpa else None,
                "ctc_min_lpa": getattr(extracted, "ctc_min_lpa", None).value if getattr(extracted, "ctc_min_lpa", None) else None,
                "ctc_max_lpa": getattr(extracted, "ctc_max_lpa", None).value if getattr(extracted, "ctc_max_lpa", None) else None,
                "drive_date": extracted.drive_date.value.isoformat() if extracted.drive_date else None,
                "application_deadline": extracted.application_deadline.value.isoformat() if getattr(extracted, "application_deadline", None) else None,
                "rounds_count": len(extracted.rounds),
            }
        except (EmptyDocumentError, CorruptDocumentError, ScannedPdfError, UnsupportedFormatError) as exc:
            error_raised = type(exc).__name__

        # Evaluate edge case handling
        if is_error_case:
            if error_raised in ("EmptyDocumentError", "CorruptDocumentError", "ScannedPdfError"):
                edge_cases_handled += 1
                doc_results.append({"filename": filename, "status": "PASS_ERROR_HANDLED", "error": error_raised})
            else:
                doc_results.append({"filename": filename, "status": "FAIL_UNCAUGHT_ERROR", "error": error_raised})
            continue

        # Evaluate fields
        all_doc_fields_match = True
        field_evals = {}

        for f in fields_to_eval:
            exp_val = gt.get(f)
            ext_val = extracted_data.get(f)

            if exp_val is not None:
                metrics[f]["total_expected"] += 1
            if ext_val is not None:
                metrics[f]["total_extracted"] += 1

            is_match = match_field(f, ext_val, exp_val)
            field_evals[f] = {"expected": exp_val, "extracted": ext_val, "match": is_match}

            if exp_val is not None and ext_val is not None:
                if is_match:
                    metrics[f]["tp"] += 1
                else:
                    metrics[f]["fp"] += 1
                    metrics[f]["mismatches"] += 1
                    all_doc_fields_match = False
            elif exp_val is not None and ext_val is None:
                metrics[f]["fn"] += 1
                all_doc_fields_match = False
            elif exp_val is None and ext_val is not None:
                metrics[f]["fp"] += 1
                all_doc_fields_match = False

        if all_doc_fields_match:
            e2e_correct += 1
            if is_scanned:
                scanned_correct += 1
            else:
                digital_correct += 1

        doc_results.append({
            "filename": filename,
            "all_fields_match": all_doc_fields_match,
            "fields": field_evals,
            "format": gt.get("document_format"),
        })

    # Calculate summary scores
    summary: dict[str, Any] = {}
    total_docs = len(ground_truth)
    valid_docs = total_docs - edge_cases_total

    field_scores: dict[str, dict[str, float]] = {}
    for f, counts in metrics.items():
        tp = counts["tp"]
        fp = counts["fp"]
        fn = counts["fn"]
        exp = counts["total_expected"]
        ext = counts["total_extracted"]

        precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 1.0
        recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 1.0
        f1 = round((2 * precision * recall) / (precision + recall), 4) if (precision + recall) > 0 else 0.0
        missing_rate = round(fn / exp, 4) if exp > 0 else 0.0
        incorrect_rate = round(counts["mismatches"] / ext, 4) if ext > 0 else 0.0
        exact_match_acc = round(tp / exp, 4) if exp > 0 else 1.0

        field_scores[f] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "exact_match_accuracy": exact_match_acc,
            "missing_field_rate": missing_rate,
            "incorrect_value_rate": incorrect_rate,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "expected": exp,
            "extracted": ext,
        }

    overall_precision = round(sum(s["precision"] for s in field_scores.values()) / len(field_scores), 4)
    overall_recall = round(sum(s["recall"] for s in field_scores.values()) / len(field_scores), 4)
    overall_f1 = round(sum(s["f1"] for s in field_scores.values()) / len(field_scores), 4)
    e2e_accuracy = round(e2e_correct / valid_docs, 4) if valid_docs > 0 else 0.0
    scanned_accuracy = round(scanned_correct / scanned_total, 4) if scanned_total > 0 else 0.0
    digital_accuracy = round(digital_correct / digital_total, 4) if digital_total > 0 else 0.0
    edge_case_rate = round(edge_cases_handled / edge_cases_total, 4) if edge_cases_total > 0 else 1.0

    return {
        "total_documents": total_docs,
        "valid_documents": valid_docs,
        "digital_documents": digital_total,
        "scanned_documents": scanned_total,
        "edge_case_documents": edge_cases_total,
        "overall_precision": overall_precision,
        "overall_recall": overall_recall,
        "overall_f1": overall_f1,
        "end_to_end_accuracy": e2e_accuracy,
        "digital_document_accuracy": digital_accuracy,
        "scanned_pdf_accuracy": scanned_accuracy,
        "edge_case_pass_rate": edge_case_rate,
        "field_scores": field_scores,
        "doc_results": doc_results,
    }


if __name__ == "__main__":
    print("Running 100-sample extraction accuracy evaluation...")
    results = evaluate()
    print("\n" + "=" * 80)
    print("IM-101 ANNOUNCEMENT EXTRACTION ACCURACY BENCHMARK REPORT")
    print("=" * 80)
    print(f"Total Documents: {results['total_documents']} (Digital: {results['digital_documents']}, Scanned: {results['scanned_documents']}, Edge Cases: {results['edge_case_documents']})")
    print(f"Overall Precision: {results['overall_precision'] * 100:.2f}%")
    print(f"Overall Recall:    {results['overall_recall'] * 100:.2f}%")
    print(f"Overall F1 Score:  {results['overall_f1'] * 100:.2f}%")
    print(f"End-to-End Accurate Documents: {results['end_to_end_accuracy'] * 100:.2f}%")
    print(f"  - Digital Documents Accuracy:  {results['digital_document_accuracy'] * 100:.2f}%")
    print(f"  - Scanned PDF (OCR) Accuracy:  {results['scanned_pdf_accuracy'] * 100:.2f}%")
    print(f"  - Error / Edge Cases Handled:  {results['edge_case_pass_rate'] * 100:.2f}%")
    print("\n" + "-" * 80)
    print(f"{'Field':<26} | {'Precision':<9} | {'Recall':<9} | {'F1':<7} | {'Exact Match':<11} | {'Missing %':<9}")
    print("-" * 80)
    for f, s in results["field_scores"].items():
        print(f"{f:<26} | {s['precision']*100:>7.2f}% | {s['recall']*100:>7.2f}% | {s['f1']*100:>5.2f}% | {s['exact_match_accuracy']*100:>9.2f}% | {s['missing_field_rate']*100:>7.2f}%")
    print("=" * 80)
