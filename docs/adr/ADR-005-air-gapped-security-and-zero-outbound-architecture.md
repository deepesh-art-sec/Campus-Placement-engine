# Architecture Decision Record (ADR-005): Air-Gapped Security & Zero-Outbound LAN Architecture

## Context & Problem Statement

Collegiate placement systems store highly sensitive student academic histories, disciplinary records, offers, and compensation data:
- Universities often operate placement drives during network outages, Wi-Fi brownouts, or in secure exam centers with disconnected networks.
- Student data must never be transmitted to external servers, commercial analytics, or third-party cloud services.
- Students must access schedules and offer statuses from their mobile phones over the college Wi-Fi/LAN without being able to view other students' data or tamper with candidate IDs.
- Regulators and audit bodies require verification that the application emits zero outbound network requests.

## Decision

We instituted an **Air-Gapped, Single-Port Local Area Network (LAN) Architecture**:

1. **Self-Contained Local Serving**:
   - `start.bat` / `start.sh` automatically discovers the active LAN interface (`192.168.x.x` or `10.x.x.x`), applies SQLite migrations, seeds default accounts, and boots FastAPI serving both REST endpoints and built SPA static assets on a single port (`8000`).
   - A single-port deployment prevents CORS issues and eliminates the need for reverse proxies or Docker.

2. **Zero Outbound Enforcement & Automated Verification**:
   - OS-level socket interception test (`test_airgap_guardrails.py`) monkeypatches `socket.socket.connect` during full pipeline execution (extraction, rule evaluation, policy checking, OR-Tools scheduling, and API calls) and asserts 0 outbound socket attempts.
   - Frontend includes an in-app "Offline Self-Check" audit panel performing browser-level verification.

3. **Multi-Layered Security Defenses**:
   - Password hashing via Argon2id (`argon2-cffi`) with cryptographically generated salts.
   - Session hardening: HTTP-only, SameSite=Lax session cookies with client CSRF double-submit token protection.
   - Field-level encryption at rest (`backend/app/security/field_crypto.py`) using AES-256 Fernet keys derived via PBKDF2 with 100,000 SHA-256 iterations.
   - Strict Content Security Policy (`default-src 'self'`) and security headers (`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`).
   - PII redaction filter in structured logging (`JsonPiiRedactingFormatter`).
   - Encrypted backup/restore (`.enc` format) and cryptographic one-click institutional wipe.

## Consequences

- **Positive**:
   - Complete operational continuity with zero internet connection.
   - 100% compliance with student data sovereignty and FERPA/DPDP regulatory standards.
   - Strict student scoping: Candidates access only their own schedule and offer-policy status via roll number + temporary code authentication.
- **Trade-offs**:
   - Frontend dependencies (fonts, icons) must be bundled locally into `dist/` rather than fetched from CDNs.
