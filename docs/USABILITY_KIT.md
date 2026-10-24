# Institutional Usability Kit & Officer Operation Protocol (Core Engine)

## Overview

This kit provides a structured usability protocol for validating the Institutional Placement Engine. It includes an interactive 3-student verification script and a 10-task officer operations checklist with target completion timings.

---

## Part 1: Three-Student Usability Protocol

### Persona A: Standard Candidate (Aryan Sharma - `PIPE_001`)
*Profile*: 8.2 CGPA, CSE branch, 0 backlogs, no existing offers.
- **Workflow**:
  1. Navigate to Candidate Portal (`http://<LAN_IP>:8000`).
  2. Authenticate with Roll No: `PIPE_001` and OTP: `123456`.
  3. Inspect drive status:
     - Drive 1 (TechCorp @ 8.0 LPA): **Eligible** ("Eligible: you meet all academic and backlog requirements for this drive.").
     - Drive 2 (InnoTech @ 12.0 LPA): **Eligible**.
  4. View personalized schedule: Zero clashes; assigned to Hall A for Online Assessment at 09:00, Cabin 1 for Technical Interview at 11:30.
  5. Click "Print Schedule Sheet" to generate clean, printer-friendly pass.
- **Expected Outcome**: Instant visibility of personalized schedule without access to other candidates' records or institutional rankings.

---

### Persona B: Complex Edge-Case Candidate (Priya Nair - `PIPE_002`)
*Profile*: Lateral entry candidate (no 12th marks, 82.5% Polytechnic Diploma), 1 cleared backlog (cleared on 2026-10-15, before drive on 2026-11-20), holding 6.0 LPA regular offer from Wipro.
- **Workflow**:
  1. Placement Officer runs eligibility for InnoTech (Dream Drive @ 12.0 LPA, Dream threshold 10.0 LPA, Diploma substitution enabled).
  2. Evaluator automatically substitutes Diploma percentage for missing 12th percentage.
  3. Evaluator validates that the backlog was cleared *prior* to the drive date, treating active backlogs as 0.
  4. Policy Engine evaluates existing 6.0 LPA offer: Approves Dream Tier upgrade under Clause 2.1 (CTC 12.0 LPA $\ge$ 10.0 LPA).
  5. Student logs in as `PIPE_002`: Sees status **Eligible (Dream Upgrade Approved)**.
- **Expected Outcome**: Fully automated qualification without requiring manual coordinator intervention or equivalency waivers.

---

### Persona C: Disputed Candidate (Rohan Gupta - `PIPE_003`)
*Profile*: Exceptional student (9.8 CGPA, clean history), holds existing 8.0 LPA offer from Infosys. Wants to appear for TechCorp (7.5 LPA).
- **Workflow**:
  1. Rohan attempts to sit for TechCorp; the engine flags him as **Policy Blocked**.
  2. Rohan raises a dispute claiming his 9.8 CGPA makes him the most deserving candidate.
  3. Officer opens "Dispute Explainer" (`/dispute`) in the Officer Workspace.
  4. Selects TechCorp, Student A (Aryan Sharma, allowed), and Student B (Rohan Gupta, blocked).
  5. Engine generates objective comparative summary:
     - *"Student Aryan Sharma (PIPE_001) holds 0 offers and is within the 1-offer quota."*
     - *"Student Rohan Gupta (PIPE_003) holds an active offer from Infosys (8.0 LPA). TechCorp offers 7.5 LPA, which does not qualify as a Dream upgrade (>= 10.0 LPA) under Clause 2.2."*
  6. Officer prints or reads the formal explanation directly to Rohan.
- **Expected Outcome**: Eliminates allegations of coordinator favoritism through mathematical policy citations and written audit justifications.

---

## Part 2: Officer 10-Task Operational Checklist

| # | Task Description | Interface Location | Target Duration | Success Metric |
| :-: | :--- | :--- | :---: | :--- |
| **1** | **One-Command Boot & LAN Discovery** | Terminal (`start.bat` / `start.sh`) | < 5 seconds | Displays local and student LAN URLs (`http://192.168.x.x:8000`) |
| **2** | **Student Roster Import & Dry-Run** | *Students & Importer* (`/students`) | < 30 seconds | Ingests 600 students from CSV/XLSX with 0 unhandled warnings |
| **3** | **Announcement Extraction & Review** | *Extract Drive* (`/create_drive`) | < 45 seconds | Extracts PDF circular into typed AST criteria with confidence badges |
| **4** | **Rule AST Customization** | *Rule Editor* (`/rule_editor`) | < 20 seconds | Visual form adjustments (e.g. branch aliases, gap limits) |
| **5** | **Policy Ambiguity Configuration** | *Offer Policies* (`/policies`) | < 20 seconds | Toggle Dream threshold inclusivity, off-campus counting, cooling days |
| **6** | **Batch Eligibility Run** | *Eligibility Runs* (`/eligibility`) | < 3 seconds | Evaluates 600 candidates with cryptographic snapshot hashes |
| **7** | **Clash-Free Schedule Generation** | *Schedule Grid* (`/schedule`) | < 5 seconds | OR-Tools CP-SAT generates schedule with **0 clashes verified** badge |
| **8** | **Interactive What-If Simulation** | *What-If & Publish* (`/what_if`) | < 2 seconds | Modifies cut-off, generates dynamic headline, previews moves |
| **9** | **Official Publish & Rollback Guard** | *What-If & Publish* (`/what_if`) | < 3 seconds | Immutable version snapshot published; one-click rollback ready |
| **10** | **Company-Formatted Shortlist Export** | *Company Export* (`/export`) | < 15 seconds | Generates custom CSV/XLSX mapping exactly to company template |

---

## Usability Verification Pass Criteria

1. **Zero Silent Data Corruption**: Importers and extractors must flag ambiguous rows or low-confidence tokens explicitly.
2. **Deterministic Reproducibility**: Running the same eligibility check or schedule generation twice yields identical snapshot hashes and slot assignments.
3. **Institutional Accountability**: Every blocked decision links directly to an explicit institutional policy clause with an actionable unblocking path.
