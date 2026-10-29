from fastapi.testclient import TestClient
from backend.app.api.main import app
from backend.app.storage.database import SessionLocal
from backend.app.storage.models.entities import UserModel

client = TestClient(app)

# 1. Login as officer
login_res = client.post("/api/auth/login", json={"username": "officer", "password": "officer123"})
assert login_res.status_code == 200, f"Login failed: {login_res.text}"
csrf = client.cookies.get("csrf_token") or ""

# 2. Test GET /api/rooms
get_res = client.get("/api/rooms")
assert get_res.status_code == 200, f"GET /api/rooms failed: {get_res.text}"
rooms = get_res.json()
print(f"Total campus rooms: {len(rooms)}")
assert len(rooms) > 0

# 3. Test POST /api/rooms/provision-for-students
prov_res = client.post(
    "/api/rooms/provision-for-students",
    json={
        "students_count": 280,
        "round_type": "interview",
        "capacity_per_room": 40,
        "preferred_building": "Academic Complex",
    },
    headers={"X-CSRF-Token": csrf},
)
assert prov_res.status_code == 200, f"Provisioning failed: {prov_res.text}"
p_data = prov_res.json()
print("Provision result:", p_data)

# 4. Test POST /api/rooms (create single classroom)
c_name = f"Classroom Test {len(rooms) + 1}"
create_res = client.post(
    "/api/rooms",
    json={
        "name": c_name,
        "building": "Academic Complex",
        "capacity": 45,
        "has_computers": True,
        "room_type": "classroom",
    },
    headers={"X-CSRF-Token": csrf},
)
assert create_res.status_code == 201, f"Create room failed: {create_res.text}"
print("Created single classroom:", create_res.json())

print("ALL CLASSROOM PROVISIONING API TESTS PASSED!")
