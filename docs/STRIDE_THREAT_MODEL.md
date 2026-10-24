# STRIDE Threat Model & Security Assurance

This document details the security architecture, threat model, and verification matrix for the **Institutional Placement Eligibility & Scheduling Engine (Core Engine)**.

---

## 1. STRIDE Threat Model & Test Mapping

| Threat Category | Potential Attack Vector | Architectural Mitigation | Verification Test |
|---|---|---|---|
| **Spoofing** | Student impersonation or brute-forcing officer / peer credentials | • OWASP-compliant Argon2id password hashing (`time_cost=2`, `memory_cost=65536`)<br>• Random 48-byte cryptographically secure session tokens (`secrets.token_urlsafe(48)`)<br>• One-time access codes for students issued on LAN by TPO | [`backend/tests/test_auth_flow.py`](backend/tests/test_auth_flow.py)<br>[`backend/tests/test_role_rbac_boundaries.py`](backend/tests/test_role_rbac_boundaries.py) |
| **Tampering** | Intercepting HTTP requests to alter candidate shortlists, eligibility verdict, or schedule slots | • Synchronizer token pattern CSRF defense (`X-CSRF-Token` validated with HMAC constant-time comparison on mutating HTTP verbs)<br>• Optimistic concurrency control via integer `version` columns rejecting stale concurrent writes<br>• Append-only event log recording every state transition | [`backend/tests/test_api_workflows.py`](backend/tests/test_api_workflows.py)<br>[`backend/tests/test_what_if_and_publish_flow.py`](backend/tests/test_what_if_and_publish_flow.py) |
| **Repudiation** | An officer or coordinator modifying cut-offs or overrides and denying the action | • Structured `audit_logs` table storing actor ID, role, client IP, timestamp, action, and JSON diffs<br>• Event-sourcing replay engine re-evaluating state at any historical sequence index | [`backend/tests/test_event_result_recording_and_dispute_comparison.py`](backend/tests/test_event_result_recording_and_dispute_comparison.py)<br>[`backend/tests/test_audit_trail_immutability.py`](backend/tests/test_api_workflows.py) |
| **Information Disclosure** | Candidate snooping peer GPAs, offer packages, or demographic data; leakage via logs | • Strictly self-scoped student endpoints: candidates can only fetch their own record (`/api/students/me/*`), with server-side ID tampering rejection<br>• AES-256 field-level encryption for sensitive columns at rest<br>• Automated PII redaction (`JsonPiiRedactingFormatter`) suppressing emails, names, DOBs, and demographic data in console logs<br>• Air-gap socket interception verifying zero telemetry outbound | [`backend/tests/test_airgap_guardrails.py`](backend/tests/test_airgap_guardrails.py)<br>[`backend/tests/test_role_rbac_boundaries.py`](backend/tests/test_role_rbac_boundaries.py) |
| **Denial of Service** | Exhausting server memory via multi-gigabyte document uploads or solving unbounded schedules | • HTTP body size capped at 15 MB in FastAPI middleware<br>• In-memory sliding-window rate limiting on login routes (5 attempts per minute per IP:username)<br>• CP-SAT solver hard timeout budget (10 to 60 seconds) with incremental fallback scheduling | [`backend/tests/test_api_workflows.py`](backend/tests/test_api_workflows.py)<br>[`backend/tests/test_scheduler.py`](backend/tests/test_scheduler.py) |
| **Elevation of Privilege** | Student or recruiter attempting administrative actions (e.g. publishing drives or changing policy) | • Role-Based Access Control (RBAC) enforced via FastAPI dependency injection: `require_officer`, `require_officer_or_coordinator`, `require_student`<br>• Recruiter queries strictly filtered by corporate `company_id` | [`backend/tests/test_role_rbac_boundaries.py`](backend/tests/test_role_rbac_boundaries.py) |

---

## 2. Air-Gap & Zero Outbound Telemetry Guarantee

1. **System Font Stack Only**: The frontend bundle contains zero Google Fonts, external CDNs, or third-party web trackers. All UI renders using the native OS system font stack (`-apple-system, Segoe UI, Roboto, sans-serif`).
2. **Socket Interception Guardrail**: Automated test suite (`test_airgap_guardrails.py`) monkeypatches Python's OS socket interface and verifies that executing student ingestion, requirement extraction, rule evaluation, constraint scheduling, what-if simulations, and XLSX exports generates **0** non-loopback connections.
3. **In-App Offline Self-Check**: The frontend UI features an in-app audit dashboard (`/views/audit/OfflineSelfCheck.tsx`) monitoring fetch activity and displaying `external calls: 0`.

---

## 3. Cryptographic Storage & Backup Specifications

- **Password Hasher**: Argon2id via `argon2-cffi`
- **Session Tokens**: 48-byte URL-safe cryptographically secure pseudorandom strings (`secrets.token_urlsafe(48)`), stored with SHA-256 indexing.
- **Encrypted Backups**: AES-256-GCM / Fernet authenticated encryption using PBKDF2HMAC (SHA-256, 100,000 iterations, 16-byte random salt).
- **Sensitive Field Encryption**: Authenticated symmetric encryption wrapper (`backend/app/security/field_crypto.py`) for student demographic attributes and contact identifiers stored at rest in SQLite.
