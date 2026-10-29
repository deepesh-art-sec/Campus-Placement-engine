# Recruitment Requirement Extraction Evaluation Report

## 1. Executive Summary

- **Dataset Evaluated**: 25 Mixed-Format Placement Announcements (.txt, .eml, .pdf, .docx)
- **Announcements Fully Extracted (Zero Manual Entry)**: **21 / 25** (84.0%)
- **Target Requirement**: At least 20 of 25 announcements without manual re-typing (Criterion 3).
- **Target Status**: **PASSED** (Achieved 21/25 fully offline).
- **Total Benchmark Execution Time**: 1.772 seconds (70.9 ms/document).
- **Cloud/Network Calls**: 0 (100% offline regex & semantic dictionary architecture).
- **LLM Dependency**: None (LLM Adapter OFF by default; target strictly achieved deterministically).

## 2. Per-Field Precision and Recall

| Field Name | Evaluated | Correct (TP) | False Pos | False Neg | Precision | Recall | F1 Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `company_name` | 25 | 25 | 0 | 0 | 100.0% | 100.0% | 100.0% |
| `drive_date` | 25 | 25 | 0 | 0 | 100.0% | 100.0% | 100.0% |
| `mode` | 25 | 25 | 0 | 0 | 100.0% | 100.0% | 100.0% |
| `ctc_lpa` | 25 | 25 | 0 | 0 | 100.0% | 100.0% | 100.0% |
| `cgpa_min` | 25 | 25 | 0 | 0 | 100.0% | 100.0% | 100.0% |
| `tenth_percentage_min` | 25 | 25 | 0 | 0 | 100.0% | 100.0% | 100.0% |
| `twelfth_percentage_min` | 25 | 25 | 0 | 0 | 100.0% | 100.0% | 100.0% |
| `active_backlogs_max` | 25 | 25 | 0 | 0 | 100.0% | 100.0% | 100.0% |
| `historical_backlogs_max` | 4 | 4 | 4 | 0 | 50.0% | 100.0% | 66.7% |
| `allowed_branches` | 25 | 24 | 0 | 1 | 100.0% | 96.0% | 98.0% |
| `gap_years_max` | 25 | 25 | 0 | 0 | 100.0% | 100.0% | 100.0% |
| `rounds_count` | 25 | 25 | 0 | 0 | 100.0% | 100.0% | 100.0% |

## 3. Document-by-Document Breakdown

| Filename | Company | Extracted Status | Confidence | Ambiguities Flagged | Review Items |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `01_google_announcement.txt` | Google | Full Extract (Zero Manual Entry) | 0.96 | 0 | 0 |
| `02_microsoft_announcement.txt` | Microsoft | Full Extract (Zero Manual Entry) | 0.95 | 0 | 0 |
| `03_amazon_announcement.txt` | Amazon | Full Extract (Zero Manual Entry) | 0.95 | 0 | 0 |
| `04_goldman_sachs_announcement.txt` | Goldman Sachs | Full Extract (Zero Manual Entry) | 0.96 | 0 | 0 |
| `05_oracle_announcement.txt` | Oracle | Full Extract (Zero Manual Entry) | 0.95 | 0 | 0 |
| `06_qualcomm_announcement.txt` | Qualcomm | Full Extract (Zero Manual Entry) | 0.95 | 0 | 0 |
| `07_cisco_announcement.txt` | Cisco | Review Required | 0.95 | 0 | 0 |
| `08_deloitte_usi_email.eml` | Deloitte USI | Full Extract (Zero Manual Entry) | 0.95 | 0 | 0 |
| `09_tata_consultancy_services_email.eml` | Tata Consultancy Services | Full Extract (Zero Manual Entry) | 0.95 | 0 | 0 |
| `10_infosys_power_programmer_email.eml` | Infosys Power Programmer | Full Extract (Zero Manual Entry) | 0.95 | 0 | 0 |
| `11_wipro_turbo_email.eml` | Wipro Turbo | Full Extract (Zero Manual Entry) | 0.95 | 2 | 2 |
| `12_accenture_advanced_tech_email.eml` | Accenture Advanced Tech | Full Extract (Zero Manual Entry) | 0.95 | 0 | 0 |
| `13_siemens_email.eml` | Siemens | Full Extract (Zero Manual Entry) | 0.95 | 0 | 0 |
| `14_larsen_and_toubro_spec.pdf` | Larsen & Toubro | Review Required | 0.96 | 0 | 0 |
| `15_texas_instruments_spec.pdf` | Texas Instruments | Full Extract (Zero Manual Entry) | 0.95 | 0 | 0 |
| `16_intel_spec.pdf` | Intel | Full Extract (Zero Manual Entry) | 0.95 | 0 | 0 |
| `17_morgan_stanley_spec.pdf` | Morgan Stanley | Full Extract (Zero Manual Entry) | 0.96 | 0 | 0 |
| `18_samsung_randd_spec.pdf` | Samsung R&D | Full Extract (Zero Manual Entry) | 0.95 | 0 | 0 |
| `19_tata_motors_spec.pdf` | Tata Motors | Review Required | 0.95 | 0 | 0 |
| `20_reliance_industries_jd.docx` | Reliance Industries | Full Extract (Zero Manual Entry) | 0.95 | 0 | 0 |
| `21_itc_limited_jd.docx` | ITC Limited | Full Extract (Zero Manual Entry) | 0.96 | 0 | 0 |
| `22_biocon_jd.docx` | Biocon | Full Extract (Zero Manual Entry) | 0.95 | 0 | 0 |
| `23_zs_associates_jd.docx` | ZS Associates | Full Extract (Zero Manual Entry) | 0.95 | 0 | 0 |
| `24_barclays_jd.docx` | Barclays | Full Extract (Zero Manual Entry) | 0.95 | 0 | 0 |
| `25_atlassian_jd.docx` | Atlassian | Review Required | 0.96 | 0 | 0 |

## 4. Ambiguity and Review Queue Governance

In compliance with institutional placement standards:
1. **Never Guess Silently**: Phrasings such as *'throughout'* or *'at time of joining'* are explicitly identified as ambiguities and automatically appended to the review queue with suggested clarification actions.
2. **Side-by-Side Review Contract**: The officer UI receives the verbatim sentence provenance alongside every parsed field, enabling 1-click accept, edit, or reject.
3. **Feedback Audit Log**: Every correction or override is persisted in the audit trail with officer ID and timestamp.

## 5. Offline & Privacy Assurance

- All text parsing, document decompression, and table extractions execute locally.
- No student data, corporate specifications, or salary details leave the local host environment.
