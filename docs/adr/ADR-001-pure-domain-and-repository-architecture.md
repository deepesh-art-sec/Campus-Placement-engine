# Architecture Decision Record (ADR-001): Pure Domain & Repository Pattern

## Context & Problem Statement

Collegiate placement cells face complex, fast-evolving operational constraints:
- Companies continuously revise CGPA thresholds, backlog rules, branch lists, and interview panel structures shortly before or during recruitment drives.
- Institutional offer policies require non-negotiable compliance tracking ("one student, one offer" with Dream exceptions, backlog clearing deadlines, and multi-tier salary progression).
- Transparency is essential: every inclusion or exclusion decision must be mathematically traceable, explainable in plain terms, and replayable from historical events.
- Strict data sovereignty requirements mandate that student records never leave institutional laptops/servers, and protected demographic attributes (gender, caste, religion, category) must never be leveraged by any eligibility filter.

## Decision

We adopt a **Pure Domain Core** paired with an **Abstract Repository & Unit of Work (UoW)** architecture:

1. **Pure Domain (`app/domain`)**:
   - Zero database, ORM, framework, or network imports.
   - All domain aggregates (`Student`, `Drive`, `RequirementSet`, `OfferPolicy`, `EligibilityDecision`, `Schedule`) are modelled using Pydantic v2 with strict validation and immutability invariants.
   - Protected demographic attributes are isolated into a standalone model (`ProtectedDemographics`) and runtime guards prevent any eligibility rule predicate from referencing protected fields.
   - Domain operations are pure deterministic functions, enabling instant unit and property-based testing.

2. **Repository Abstraction (`app/storage/repositories/interfaces.py`)**:
   - PEP 544 Protocols define clear contracts for student, drive, policy, eligibility, schedule, and event storage.
   - Domain and application services interact solely with protocols, remaining decoupled from SQLAlchemy.

3. **Storage & Persistence (`app/storage`)**:
   - Relational persistence in SQLite running in Write-Ahead Logging (WAL) mode with synchronous normal for maximum concurrent read performance on local hardware.
   - Foreign key constraints are enforced on every database connection (`PRAGMA foreign_keys = ON`).
   - Optimistic concurrency control is implemented via monotonically increasing `version` columns, rejecting stale updates with `ConcurrencyConflictError`.

4. **Event Sourcing & Audit (`app/events`)**:
   - All state mutations (student imports, rule revisions, policy overrides, schedule runs) are recorded as immutable, append-only events with actor tracking, timestamps, and field-level before/after diffs.
   - The engine can rebuild the state of any student, policy, or drive at any historical timestamp for audit hearings.

5. **Audited Multi-Format Importer (`app/importers`)**:
   - Parses CSV and XLSX files, auto-guessing column headers with manual overrides.
   - Normalises messy values (percentages, fractions, 4.0 vs 10.0 CGPA scales, branch aliases) while strictly adhering to a non-silent principle: every correction is captured as a distinct row-level warning.
   - Provides a non-destructive dry-run mode that audits and previews files before database commitment.

## Consequences

- **Positive**:
  - Domain rules can be tested in sub-milliseconds without spinning up databases.
  - Zero lock-in to SQLAlchemy or SQLite; the storage backend can be swapped or extended without modifying domain logic.
  - Complete compliance with institutional privacy standards and audit transparency requirements.
  - High resilience against concurrent modifications during intense multi-coordinator placement drives.
- **Trade-offs**:
  - Mapping boilerplate between ORM entities and pure domain models (managed via explicit, tested mappers).
