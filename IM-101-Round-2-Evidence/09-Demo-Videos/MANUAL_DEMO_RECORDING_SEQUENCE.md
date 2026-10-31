# IM-101 CAMPUS PLACEMENT ENGINE
## Round 2 Prototype Validation — Manual Demo Video Recording Sequence

This document provides a precise, timestamped manual recording script to demonstrate the live, running IM-101 application workflows from end-to-end.

**Target Duration**: 4 to 6 minutes  
**Application URL**: `http://localhost:5173`  
**Backend API**: `http://localhost:8000/api`  
**Recording Resolution**: 1920x1080 (Full HD, 60fps recommended)

---

### Phase 1: Authentication & Portal Login (0:00 - 0:35)
1. **[0:00]** Open browser to `http://localhost:5173`.
2. **[0:05]** Point to the Enterprise Login Portal. Show role selection options: *Placement Officer, Drive Coordinator, Recruiter, Student Candidate*.
3. **[0:15]** Click **Placement Officer** button (loads `admin` / `admin123`).
4. **[0:20]** Click **Sign In to Enterprise Portal**. Show instant authentication and transition to the Officer Overview.

---

### Phase 2: Officer & Coordinator Dashboard Overview (0:35 - 1:15)
1. **[0:35]** Walk through the **Main Corporate Dashboard**:
   - Highlight the 4 KPI cards: **18 Companies**, **1,838 Students**, **19 Drives**, **328 Offers**.
2. **[0:50]** Scroll to the **Recent Placement Drives** table showing TCS, Infosys, Wipro, Amazon, and Accenture with status badges (`Upcoming`, `In Progress`).
3. **[1:05]** Demonstrate the **Quick Actions** toolbar: Upload Announcement, Add Drive, Manage Students, Generate Schedule.

---

### Phase 3: Announcement Upload & Gemini Hybrid NLP Extraction (1:15 - 2:20)
1. **[1:15]** Navigate to the **Review & Create Drive** page (`/review`).
2. **[1:25]** Show the document upload dropzone supporting PDF, DOCX, TXT, EML, and direct Images.
3. **[1:35]** Select a preloaded sample notice (e.g. *Goldman Sachs* or *Morgan Stanley*). Show full circular text in the source preview.
4. **[1:45]** Click **Run Extraction / Parse**.
5. **[1:55]** Point out the real-time extraction results powered by **Gemini 3.5 Flash-Lite**:
   - Company Name: `Goldman Sachs` (Confidence: 96%)
   - Job Role: `Systems Engineer`
   - CTC: `22.5 LPA` | Monthly Stipend: `₹50,000`
   - Minimum CGPA Cutoff: `7.50`
   - Allowed Engineering Branches: `CSE`, `IT`, `ECE`
   - Backlog Policy: `0 Active Backlogs (No Standing Arrears)`
   - Ordered Selection Stages: `Online Test`, `Technical Interview`, `HR Interview`
6. **[2:10]** Highlight the side-by-side verification form and editable fields with verification badges.

---

### Phase 4: Student Registry & Academic Profiles (2:20 - 3:00)
1. **[2:20]** Navigate to the **Student Registry** (`/students`).
2. **[2:30]** Show the 1,838 candidate records. Demonstrate instant search by typing `CSE` or roll number `BT210042`.
3. **[2:40]** Click on a candidate row to expand the **Student Profile Drawer**:
   - Show personal biographical info, category, and contact details.
   - Display semester-wise academic marks and SGPA trajectory.
   - Show active backlog audit (`0`) and existing offer history.

---

### Phase 5: Eligibility Engine & Rejection Audit Trace (3:00 - 3:45)
1. **[3:00]** Navigate to the **Eligibility Engine** (`/eligibility`).
2. **[3:10]** Select an upcoming placement drive (e.g., *Amazon SDE-1*).
3. **[3:20]** Show the list of **Eligible Candidates** verified by the mathematical rule engine.
4. **[3:30]** Toggle to the **Ineligible / Rejected Candidates** tab.
5. **[3:38]** Click on a rejected candidate to display the exact **Rejection Trace**:
   - E.g.: `CGPA 6.4 < 7.0 required by policy` or `1 Active Backlog exceeds threshold of 0`.

---

### Phase 6: Automated Scheduling & OR-Tools Clash Detection (3:45 - 4:45)
1. **[3:45]** Navigate to the **Scheduling & Clash Matrix** (`/schedule`).
2. **[3:55]** Display the **0 Clashes Verified (Mathematically Proven) Guaranteed** status badge.
3. **[4:10]** Walk through the physical campus venue allocation across **Classrooms 101, 102, 103, 104** and 30-minute time intervals (`09:00`, `09:30`, `10:00`, `10:30`, `11:00`).
4. **[4:25]** Point out individual student slot cards (e.g., *Tarun Nambiar BT210042 in Classroom 101 at 09:30*).
5. **[4:35]** Emphasize mathematical proof that **0 students are double-booked** and **0 rooms conflict**.

---

### Phase 7: Analytics Reports & Data Export (4:45 - 5:20)
1. **[4:45]** Navigate to the **Reports & Export** module (`/export`).
2. **[4:55]** Display the executive placement analytics:
   - Branch-wise placement conversion charts.
   - Offer tier distribution (Super Dream, Dream, Core, Regular).
3. **[5:10]** Demonstrate the Export facility: Click **Export to CSV / Excel** to trigger instant client-side download.

---

### Phase 8: Candidate Portal & Wrap-up (5:20 - 5:45)
1. **[5:20]** Switch session to **Candidate Portal** (Login as student `BT210001` / `123456`).
2. **[5:30]** Show student's personalized view: verified eligibility status for active drives, upcoming interview slot timetable, and offer letter notices.
3. **[5:45]** Conclude demo recording.
