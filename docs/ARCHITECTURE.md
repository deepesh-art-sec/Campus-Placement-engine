# Institutional Placement Engine Architecture (Core Engine)

## Executive Summary

The Institutional Placement Engine is an air-gapped, zero-cloud system engineered to coordinate high-volume collegiate placement seasons. It provides deterministic academic eligibility evaluation, live institutional offer policy enforcement, NLP requirement extraction from announcement documents, constraint-based clash-free test/interview scheduling, and what-if impact simulation.

---

## 1. C4 Context Diagram

```mermaid
flowchart TD
    Officer["Placement Officer<br>(Full Control, Policy Overrides, Publish)"]
    Coord["Student Coordinator<br>(Roster Import, Schedule View)"]
    Candidate["Student Candidate<br>(LAN Scoped View: Own Schedule & Status)"]
    Recruiter["Company Recruiter<br>(Read-Only: Company Shortlist & Panels)"]

    subgraph Institutional_LAN["Institutional Local Area Network (Air-Gapped)"]
        Engine["Campus Placement Engine<br>(FastAPI + React SPA on Port 8000)"]
        Database[("Encrypted Local SQLite<br>(WAL Mode, PRAGMA foreign_keys=ON)")]
    end

    Officer -->|"Administer Drives, Rules, Schedules"| Engine
    Coord -->|"Upload Rosters, Monitor Attendance"| Engine
    Candidate -->|"View Status & Personalized Schedule"| Engine
    Recruiter -->|"Download Shortlist & Interview Roster"| Engine
    Engine <-->|"Zero-Network Relational Persistence"| Database
```

---

## 2. C4 Container Diagram

```mermaid
flowchart LR
    subgraph Client_Tier["Client Tier (Browsers on Campus LAN)"]
        OfficerSPA["Officer Workspace SPA<br>(React 18 + Vite + Tailwind CSS)"]
        StudentSPA["Student Mobile Portal<br>(Responsive Single-Page App)"]
    end

    subgraph Application_Tier["Local Application Server (Port 8000)"]
        StaticServer["Static File Server<br>(Serves SPA App-Shell from /dist)"]
        AuthMiddleware["Argon2id Auth & Session Guard<br>(HttpOnly Cookies + CSRF)"]
        APIRouter["FastAPI REST API<br>(Pydantic Input Validation)"]

        subgraph Pure_Domain["Pure Domain Core (No I/O, Pure Logic)"]
            RuleEngine["AST Rule Evaluator<br>(Eligibility Evaluator)"]
            PolicyEngine["Offer Policy Checker<br>(Live Quota & Upgrades)"]
            SchedulerEngine["OR-Tools CP-SAT<br>(Constraint Scheduler)"]
            WhatIfEngine["What-If Impact Engine<br>(In-Memory Delta Engine)"]
            Extractor["Deterministic Extractor<br>(pdfplumber + regex)"]
        end

        RepoLayer["Repository & UoW Layer<br>(SQLAlchemy ORM Decoupled via Protocols)"]
    end

    subgraph Data_Tier["Encrypted Local Storage"]
        SQLiteDB[("SQLite Database<br>(AES-256 Encrypted Columns)")]
        EncBackups[("PBKDF2 Encrypted Backups<br>(.enc Archive)")]
    end

    OfficerSPA -->|"REST over LAN"| AuthMiddleware
    StudentSPA -->|"REST over LAN"| AuthMiddleware
    AuthMiddleware --> APIRouter
    APIRouter --> Pure_Domain
    Pure_Domain <--> RepoLayer
    RepoLayer <--> SQLiteDB
    RepoLayer -.->|"Encrypted Snapshot"| EncBackups
```

---

## 3. Pure-Domain Architectural Blueprint

The system strictly decouples business domain logic from infrastructure dependencies:

```mermaid
flowchart TD
    subgraph Domain_Entities["Domain Models (Pydantic v2 Immutable Aggregates)"]
        Student["Student Aggregate<br>(Academics, Backlogs, Gaps, Offers)"]
        Drive["Drive Aggregate<br>(Company, CTC, Rounds, Panels)"]
        RuleSet["RuleSet AST<br>(CGPA, Backlogs, Branches, Age, Gaps)"]
        Policy["CollegeOfferPolicy<br>(Quotas, Dream Tiers, Multipliers)"]
    end

    subgraph Pure_Engines["Deterministic Functional Engines"]
        Evaluator["EligibilityEvaluator<br>evaluate(student, ruleset)"]
        Checker["policy_check<br>policy_check(student, drive, policy)"]
        Scheduler["PlacementSchedulerEngine<br>solve(drives, rooms, candidates)"]
        WhatIf["WhatIfEngine<br>apply_change(state, delta)"]
    end

    subgraph Results["Explainable Domain Verdicts"]
        Decision["DetailedEligibilityDecision<br>(Overall Verdict, Passed/Failed Rules, Hash)"]
        PolicyVerdict["PolicyCheckResult<br>(Status, Clause ID, Reason, What Unblocks)"]
        ScheduleGrid["ScheduleResult<br>(0 Clashes Verified, Grid Slots)"]
        Impact["ImpactReport<br>(Added/Removed, Dynamic Headline)"]
    end

    Student & RuleSet --> Evaluator --> Decision
    Student & Drive & Policy --> Checker --> PolicyVerdict
    Decision & PolicyVerdict --> Scheduler --> ScheduleGrid
    ScheduleGrid & PolicyVerdict --> WhatIf --> Impact
```

---

## 4. Sequence Diagram: What-If Simulation Workflow

Demonstrates how placement officers evaluate proposed cut-off or policy changes with instant in-memory feedback and zero database mutation:

```mermaid
sequenceDiagram
    autonumber
    actor Officer as Placement Officer
    participant UI as What-If Panel (UI)
    participant API as FastAPI /api/what-if
    participant Engine as What-If Domain Engine
    participant AST as Rule Engine & Policy Checker
    participant DB as SQLite DB

    Officer->>UI: Adjusts CGPA cut-off (e.g. 7.0 -> 6.5)
    UI->>API: POST /api/what-if/preview (DriveId, Delta)
    API->>DB: Fetch current Student & Drive state
    DB-->>API: Active Domain Aggregates
    API->>Engine: apply_change(current_state, delta)
    Note over Engine: Pure in-memory simulation (No DB mutation)
    Engine->>AST: Re-evaluate affected candidate pool
    AST-->>Engine: Delta shortlists & offer policy impacts
    Engine->>Engine: Run minimal-disturbance clash check
    Engine->>Engine: Compute data-driven dynamic headline
    Engine-->>API: ImpactReport (Added, Removed, Clashes, Headline)
    API-->>UI: 200 OK (JSON Impact Report)
    UI-->>Officer: Displays "Lowering cut-off adds 38 students; 6 clash with Northwind"
```

---

## 5. Sequence Diagram: Clash-Free Constraint Scheduling

Demonstrates the OR-Tools CP-SAT constraint formulation solving 600 students across 12 drives in ~1 second:

```mermaid
sequenceDiagram
    autonumber
    actor Officer as Placement Officer
    participant UI as Scheduler Workspace
    participant API as FastAPI /api/schedule
    participant Solver as PlacementSchedulerEngine (OR-Tools)
    participant Model as CP-SAT Constraint Model
    participant DB as SQLite DB

    Officer->>UI: Clicks "Generate Clash-Free Schedule"
    UI->>API: POST /api/schedule/run (DriveIds, RoomIds, Config)
    API->>DB: Query eligible candidates & room availability
    DB-->>API: Shortlisted Candidates, Rooms, Panels
    API->>Solver: build_and_solve(drives, rooms, candidates)
    Solver->>Model: Create Interval Variables (15-min slots)
    Solver->>Model: Add Room NoOverlap Constraints
    Solver->>Model: Add Panel NoOverlap Constraints
    Solver->>Model: Add Student NoOverlap Constraints (with walking buffer)
    Solver->>Model: Add Soft Objectives (Minimize waiting, balance panels)
    Solver->>Solver: Solve CP-SAT Model (deterministic offline)
    Solver-->>API: ScheduleResult (Feasible, 0 Clashes, 312 Scheduled Items)
    API->>DB: Persist Schedule & Slots (Draft Version)
    API-->>UI: 200 OK (Interactive Rooms x Time Grid)
    UI-->>Officer: Displays Schedule Board with "0 Clashes Verified" Badge
```

---

## 6. Relational Database Schema (ERD)

```mermaid
erDiagram
    STUDENTS ||--o{ ACADEMIC_RECORDS : "has"
    STUDENTS ||--o{ BACKLOGS : "has"
    STUDENTS ||--o{ GAP_YEARS : "has"
    STUDENTS ||--o{ OFFERS : "holds"
    STUDENTS ||--o{ ELIGIBILITY_DECISIONS : "evaluated"

    COMPANIES ||--o{ DRIVES : "conducts"
    DRIVES ||--o{ DRIVE_REQUIREMENT_VERSIONS : "versions"
    DRIVES ||--o{ PANELS : "hosts"
    DRIVES ||--o{ SCHEDULE_SLOTS : "includes"
    DRIVES ||--o{ ELIGIBILITY_DECISIONS : "receives"

    ROOMS ||--o{ SCHEDULE_SLOTS : "accommodates"
    SCHEDULES ||--o{ SCHEDULE_SLOTS : "contains"

    STUDENTS {
        string id PK
        string roll_no UK
        string name
        string email
        string branch
        string program
        float cgpa
        float tenth_percentage
        float twelfth_percentage
        float diploma_percentage
        date date_of_birth
        string gender_encrypted
        string caste_encrypted
        int version
    }

    ACADEMIC_RECORDS {
        string id PK
        string student_id FK
        int semester
        float sgpa
    }

    BACKLOGS {
        string id PK
        string student_id FK
        string subject
        int semester
        string status
        date cleared_on
    }

    OFFERS {
        string id PK
        string student_id FK
        string company
        float ctc_lpa
        float fixed_pay_lpa
        date offer_date
        string source
        string status
        boolean is_dream
    }

    DRIVES {
        string id PK
        string company_id FK
        string company_name
        date drive_date
        string mode
        float ctc_lpa
        boolean is_dream
        string status
        int version
    }

    SCHEDULE_SLOTS {
        string id PK
        string schedule_id FK
        string drive_id FK
        string room_id FK
        string student_id FK
        int round_number
        datetime start_time
        datetime end_time
    }

    ROOMS {
        string id PK
        string name
        string room_type
        int capacity
        boolean has_computers
    }

    ELIGIBILITY_DECISIONS {
        string id PK
        string student_id FK
        string drive_id FK
        string status
        string overall_student_reason
        string data_snapshot_hash
        datetime evaluated_at
    }
```
