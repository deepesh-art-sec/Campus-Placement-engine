# IMATS ERP Integration Architecture

This document specifies the integration architecture between the Collegiate Placement Engine and IMATS (Institutional Management & Academic Tracking System) or enterprise campus ERPs.

---

## 1. Architectural Pattern: Hexagonal Ports and Adapters

The placement engine isolates external enterprise systems behind an explicit domain port:
- **Port Interface**: [`backend.app.integrations.imats.interface.IIMATSClient`](backend/app/integrations/imats/interface.py)
- **Production/Sandbox Adapter**: [`backend.app.integrations.imats.client.SandboxIMATSClient`](backend/app/integrations/imats/client.py)
- **Offline Outbox Engine**: [`backend.app.integrations.imats.outbox.IMATSOutboxManager`](backend/app/integrations/imats/outbox.py)

---

## 2. Key Reliability Guarantees

### A. Idempotency Keys
Every outbound sync operation (`push_shortlist`, `push_schedule`) requires an unguessable `idempotency_key`. The server and client deduplicate duplicate submissions, guaranteeing that network reconnects or retry storms never duplicate records or schedule slots.

### B. Exponential Backoff with Jitter
When transient network interruptions occur across the college intranet, the client performs exponential backoff:
$$\text{delay} = \text{initial\_backoff} \times 2^{\text{attempt}}$$
By default, the client makes 3 retry attempts before delegating to the offline outbox.

### C. Offline Outbox Pattern
When the campus LAN is severed or the remote IMATS server is in a maintenance window:
1. Shortlists and schedules are persisted to the local outbox marked as `PENDING`.
2. When connectivity is re-established, the officer or background automation calls `/api/imats/sync` to flush pending items reliably.

---

## 3. How to Swap in the Live Production Endpoint

To connect to a live institutional IMATS ERP instance:

1. Create a concrete class `LiveIMATSClient` implementing `IIMATSClient`:
   ```python
   import httpx
   from backend.app.integrations.imats.interface import IIMATSClient

   class LiveIMATSClient(IIMATSClient):
       def __init__(self, base_url: str, api_token: str):
           self.base_url = base_url
           self.headers = {
               "Authorization": f"Bearer {api_token}",
               "Content-Type": "application/json",
           }

       def push_shortlist(self, drive_id: str, student_ids: list[str], idempotency_key: str):
           resp = httpx.post(
               f"{self.base_url}/api/v1/drives/{drive_id}/shortlist",
               json={"student_ids": student_ids},
               headers={**self.headers, "Idempotency-Key": idempotency_key},
               timeout=15.0,
           )
           resp.raise_for_status()
           return resp.json()
   ```

2. Register the live adapter in `backend/app/api/main.py` using standard dependency injection:
   ```python
   imats_client = LiveIMATSClient(
       base_url=os.getenv("IMATS_BASE_URL", "https://imats.college.edu/api"),
       api_token=os.getenv("IMATS_API_TOKEN", "secret"),
   )
   ```
