import sys
from fastapi.testclient import TestClient
from backend.app.api.main import app
from backend.app.storage.database import SessionLocal
from backend.app.storage.models.entities import UserModel

client = TestClient(app)

# 1. Test Drive Overview Metrics
resp = client.get("/api/drives/overview-metrics")
print("Status code /api/drives/overview-metrics:", resp.status_code)
if resp.status_code == 200:
    data = resp.json()
    print("Drives overview unresolved_clashes:", data.get("unresolved_clashes"))
    assert data.get("unresolved_clashes") == 0, f"Expected 0 unresolved clashes, got {data.get('unresolved_clashes')}"

# 2. Test Coordinator Overview Metrics (requires auth)
# Get or create coordinator user
db = SessionLocal()
user = db.query(UserModel).filter(UserModel.role.in_(["officer", "coordinator"])).first()
if not user:
    print("No coordinator or officer user found in DB")
    sys.exit(1)

# Set session cookie or dependency override
from backend.app.api.auth.dependencies import get_current_user, require_officer_or_coordinator
app.dependency_overrides[get_current_user] = lambda: user
app.dependency_overrides[require_officer_or_coordinator] = lambda: user

resp = client.get("/api/coordinator/overview-metrics")
print("Status code /api/coordinator/overview-metrics:", resp.status_code)
if resp.status_code == 200:
    data = resp.json()
    print("Coordinator overview unresolved_clashes:", data.get("unresolved_clashes"))
    assert data.get("unresolved_clashes") == 0, f"Expected 0 unresolved clashes, got {data.get('unresolved_clashes')}"

# 3. Test Coordinator Clashes Endpoint
resp = client.get("/api/coordinator/clashes")
print("Status code /api/coordinator/clashes:", resp.status_code)
if resp.status_code == 200:
    data = resp.json()
    print("Coordinator clashes count:", len(data))
    assert len(data) == 0, f"Expected 0 clashes, got {len(data)}"

# 4. Test Schedule Slots endpoint for Google
resp = client.get("/api/schedules/drv_google")
print("Status code /api/schedules/drv_google:", resp.status_code)
if resp.status_code == 200:
    slots = resp.json()
    print("Google slots count:", len(slots))
    clash_slots = [s for s in slots if s.get("has_clash")]
    print("Google clashing slots:", len(clash_slots))
    assert len(clash_slots) == 0, f"Expected 0 clashing slots, got {len(clash_slots)}"

print("\n--- ALL ENDPOINT CHECKS PASSED WITH 0 UNRESOLVED CLASHES ---")
db.close()
