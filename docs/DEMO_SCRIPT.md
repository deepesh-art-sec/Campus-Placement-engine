# Five-Minute Offline Demo Script (Wi-Fi Turned Off)

**Target Presentation Time**: 5 minutes 30 seconds  
**Network State**: Strict Offline (Airplane Mode / Disconnected Wi-Fi)  
**Host Machine**: Standard Laptop (macOS, Windows, or Linux)  

---

### Pre-Demo Preparation (10 Seconds Before Pitch)
In your terminal, execute:
```bash
python scripts/reset_demo.py
python scripts/lan_launcher.py
```
*Note: Your browser opens automatically at `http://localhost:8000` with pre-seeded demo accounts and clean state.*

---

### Minute 0:00 – 1:00: The Tuesday Morning Crisis (Problem Core Engine)
- **Speaker Action**: Address the jury with Wi-Fi visually disabled.
- **Narrative**:
  > *"Every placement season, university placement cells face a nightmare: 600 students, 12 concurrent companies, 8 interview rooms, and a barrage of last-minute email updates. A student eligible for TechCorp at 7.0 CGPA receives an offer at 10 AM, becoming instantly policy-blocked for an afternoon drive. Two companies demand the same seminar hall at 11 AM. One coordinator uses an outdated spreadsheet, and a candidate with a cleared backlog is wrongfully barred.*
  >
  > *Today, we present the **Institutional Placement Engine**: a 100% offline, mathematically verified platform running on a single laptop that eliminates eligibility disputes, automates policy enforcement, and schedules hundreds of students across dozens of companies in under two seconds."*

---

### Minute 1:00 – 2:15: Zero-Touch Requirement Extraction
- **Speaker Action**:
  1. Log into the Officer Workspace as `officer` / `officer123`.
  2. Click **Extract Drive** (`/create_drive`).
  3. Paste a messy recruitment circular or select sample circular text.
  4. Click **Extract Requirements**.
- **Demonstration Highlights**:
  - Show the side-by-side verification pane: raw announcement on the left, structured criteria on the right.
  - Point out that CGPA (`7.5`), branch list (`CSE, IT`), active arrears (`0`), and package (`14.0 LPA`) were extracted deterministically in 15 milliseconds without an internet connection or LLM hallucination.
  - Point out the exact source sentence cited for every field.
  - Click **Create Drive & Ruleset**.

---

### Minute 2:15 – 3:30: Pure-Domain Eligibility & Edge Cases
- **Speaker Action**:
  1. Navigate to **Policy Simulator** (`/policy_simulator`).
  2. Select Candidate `PIPE_002` (Priya Nair).
  3. Select Drive `InnoTech Labs (14.0 LPA)`.
  4. Click **Run Simulation**.
- **Demonstration Highlights**:
  - Point to the live breakdown:
    - **Diploma Substitution**: The candidate lacks a 12th percentage, but her 82.5% Polytechnic Diploma is automatically substituted by the AST evaluator.
    - **Backlog Temporal Horizon**: Her backlog in Engineering Mathematics was cleared on October 15th, *before* today's drive, so it counts as 0 active arrears.
    - **Dream Upgrade Approval**: Although she holds a 6.0 LPA offer from Wipro, InnoTech offers 14.0 LPA (above the 10.0 LPA Dream threshold), approving her upgrade under Policy Clause 2.1.
  - Toggle the Dream Threshold in the sandbox from `10.0` to `15.0 LPA` and re-run: the verdict instantly flips to **Policy Blocked (Clause 2.2)** in 18 ms!

---

### Minute 3:30 – 4:30: 1-Second Clash-Free Scheduling & What-If
- **Speaker Action**:
  1. Navigate to **Schedule Grid** (`/schedule`).
  2. Click **Generate Clash-Free Schedule**.
- **Demonstration Highlights**:
  - The CP-SAT solver computes an optimal schedule in **1.05 seconds**.
  - Show the green badge: **"0 Clashes Verified Across 312 Round Assignments"**.
  - Highlight the 15-minute inter-block walking buffer automatically inserted between consecutive interviews.
  - Navigate to **What-If & Publish** (`/what_if`).
  - Adjust the cut-off threshold: show the live headline: *"Lowering cut-off adds 38 students; 6 clash with Northwind test."*
  - Emphasize that what-if runs purely in memory with zero database side-effects until official publication.

---

### Minute 4:30 – 5:00: Candidate Scoped Access & Dispute Resolution
- **Speaker Action**:
  1. Open an incognito browser window at `http://localhost:8000`.
  2. Select the Student tab and log in as `PIPE_001` with OTP `123456`.
- **Demonstration Highlights**:
  - Show candidate-scoped access: Aryan sees *only* his personalized schedule and plain-English status. No peer rankings, no other candidates' data.
  - Click "Print Schedule Pass": renders a clean, printable pass ready for examination hall entry.
  - Switch back to the Officer console -> **Dispute Explainer** (`/dispute`).
  - Compare Aryan (`PIPE_001`, allowed) with Rohan (`PIPE_003`, 9.8 CGPA, blocked by strict one-offer). Show the formal written comparative summary that resolves student disputes without coordinator bias.

---

### Minute 5:00 – 5:30: Air-Gap Verification & Institutional Safeguards
- **Speaker Action**:
  1. Navigate to the **Offline Audit** tab (`/offline_audit`).
  2. Click **Run Air-Gap Self-Check**.
- **Demonstration Highlights**:
  - Show the live verification: **0 Outbound Connections**, **Strict Socket Interception Active**, **AES-256 Encryption at Rest Verified**.
  - Conclude with the closing pitch:
    > *"With one command, under zero internet connectivity, the Institutional Placement Engine transforms placement season chaos into a transparent, mathematically verified, clash-free reality. Thank you."*
