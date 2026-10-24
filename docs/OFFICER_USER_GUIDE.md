# Institutional Placement Engine: Placement Officer & Coordinator Guide (v1.0.0)

## Welcome to the Campus Placement Engine

The Institutional Placement Engine is a purpose-built, 100% offline platform designed to orchestrate complex campus recruitment seasons. It operates directly on institutional laptops or local servers without requiring an internet connection, cloud subscriptions, or Docker.

---

## 1. Quick Launch & Single-Port LAN Deployment

1. **Launch the Engine**:
   - Double-click `start.bat` (Windows) or execute `./start.sh` (Linux/macOS) in the root directory.
   - Alternatively, execute:
     ```bash
     python scripts/lan_launcher.py
     ```
2. **Access the Application**:
   - **Local Officer Console**: `http://localhost:8000`
   - **Candidate & Recruiter LAN Access**: The launcher automatically prints your active local IP (e.g. `http://192.168.1.45:8000`). Distribute this URL to students across the college Wi-Fi.
3. **Default Credentials**:
   - **Placement Officer**: Username: `officer` | Password: `officer123`
   - **Placement Coordinator**: Username: `coordinator` | Password: `coord123`
   - **Sample Student**: Roll No: `PIPE_001` | OTP: `123456`

---

## 2. Ingesting Candidate Rosters (CSV / XLSX)

1. Open the **Students & Importer** tab (`/students`).
2. Drag and drop your college master spreadsheet (`.xlsx` or `.csv`).
3. **Automatic Column Matching**: The engine auto-detects common header variants (`Roll Number`, `RegNo`, `CGPA`, `10th %`, `Backlogs`). Manually map any unmatched columns.
4. **Dry-Run Audit**: Click **Audit & Preview**. The engine checks:
   - Scale conversions (4.0 to 10.0 CGPA).
   - Branch aliases (e.g., "CompSci" -> "Computer Science and Engineering").
   - Invalid dates and formatting issues.
5. Review the row-level audit table. If satisfactory, click **Commit Ingestion** to save records.

---

## 3. Extracting Drive Requirements from Circulars

1. Open the **Extract Drive** tab (`/create_drive`).
2. Provide the announcement document:
   - Paste raw email text directly, OR
   - Upload a PDF circular (digital text and tables are automatically parsed), OR
   - Upload a Word bulletin (`.docx`).
3. Click **Extract Requirements**.
4. **Side-by-Side Verification**:
   - Left side shows the raw document with highlighted source sentences.
   - Right side displays parsed fields (CGPA cut-off, branch list, backlog policy, package/CTC, interview rounds).
   - Confidence badges indicate extraction certainty. Confirm any low-confidence fields and click **Create Drive & Ruleset**.

---

## 4. Configuring Rules & Policy Toggles

1. **Rule Editor (`/rule_editor`)**:
   - Visual forms allow adjusting cut-offs, branch aliases, maximum allowed backlogs, and gap-year ceilings without code.
   - Live candidate counter shows the number of eligible candidates updating in real time.
2. **Offer Policy Settings (`/policies`)**:
   - Select an institutional policy model (Strict One-Offer, Progressive 1.5x Multiplier, or Tiered Quota).
   - Configure institutional interpretation toggles:
     - *Is Dream threshold inclusive?* (e.g. is 10.0 LPA exactly treated as Dream?).
     - *Do off-campus offers count against quota?*
     - *Mandatory cooling window duration (days).*

---

## 5. Running Batch Eligibility & Audit Verification

1. Open the **Eligibility Runs** tab (`/eligibility`).
2. Select the recruitment drive and click **Run Batch Eligibility**.
3. The engine evaluates all candidates in milliseconds:
   - Categorizes students into **Eligible**, **Ineligible**, and **Policy Blocked**.
   - Generates single-line plain-English explanations for candidates.
   - Calculates a cryptographic SHA-256 snapshot hash ensuring audit reproducibility.
4. Export the resulting shortlist or proceed directly to scheduling.

---

## 6. Generating Clash-Free Schedules (OR-Tools CP-SAT)

1. Open the **Schedule Grid** tab (`/schedule`).
2. Select participating drives, available rooms (auditoriums, labs, interview cabins), and date windows.
3. Click **Generate Clash-Free Schedule**.
4. The CP-SAT solver computes an optimal timetable in seconds:
   - **Zero Room Overlaps**: No two companies book the same hall simultaneously.
   - **Zero Panel Clashes**: Interviewers are assigned non-overlapping student slots.
   - **Zero Candidate Clashes**: Students appearing for multiple drives are guaranteed collision-free slots with walking buffers between campus blocks.
5. The UI renders an interactive **Rooms $\times$ Time** grid. Drag and drop slots if manual adjustments are needed; the engine instantly flags any new clashes.

---

## 7. What-If Simulation & Publish Workflow

1. Open the **What-If & Publish** tab (`/what_if`).
2. Before publishing changes, simulate prospective adjustments:
   - E.g., lowering CGPA cut-off from 7.0 to 6.5, adding an interview panel, or marking a room unavailable.
3. The engine computes an instant **Impact Report**:
   - Generates a data-driven headline: *"Lowering cut-off adds 38 students; 6 clash with Northwind test."*
   - Previews schedule movements required to restore zero-clash integrity.
4. Click **Publish Official Schedule** to lock in an immutable version snapshot.
5. In case of unexpected changes, click **Rollback to Previous Version** for instant state recovery.

---

## 8. Result Entry & Automated Enforcement ChangeSets

1. Open the **Result Entry** tab (`/results`).
2. Enter company hiring outcomes (offers accepted, rejected, or revoked).
3. The engine computes a live **Enforcement ChangeSet**:
   - Identifies students who now exceed offer quotas.
   - Automatically cancels downstream test/interview reservations for blocked students.
   - Frees up interview slots for waiting-list candidates.

---

## 9. Resolving Candidate Disputes

1. Open the **Dispute Explainer** tab (`/dispute`).
2. When a student questions why a peer was permitted to interview while they were blocked:
   - Select the recruitment drive.
   - Select Candidate A (allowed) and Candidate B (blocked).
3. The engine generates an objective side-by-side justification citing the exact rule AST nodes and policy clauses, completely eliminating subjective allegations.

---

## 10. Data Protection, Encrypted Backups & Institutional Wipe

1. **Air-Gap Verification**:
   - Visit the **Offline Audit** tab (`/offline_audit`) to verify that 0 external network requests are being made.
2. **Encrypted Backups**:
   - Export an AES-256 encrypted database backup via the CLI:
     ```bash
     python scripts/backup_restore.py backup --passphrase "InstitutionalSecretKey"
     ```
3. **Restore Database**:
   - Restore state on a clean machine:
     ```bash
     python scripts/backup_restore.py restore my_backup.enc --passphrase "InstitutionalSecretKey"
     ```
4. **Institutional Wipe**:
   - At the conclusion of the academic year, wipe all student records and credentials by issuing the cryptographic wipe confirmation: `"CONFIRM_INSTITUTIONAL_WIPE"`.
