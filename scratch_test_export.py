from fastapi.testclient import TestClient
from backend.app.api.main import app

client = TestClient(app)

# Test Officer Login & Export
login_resp = client.post("/api/auth/login", json={"username": "officer", "password": "officer123"})
print("Officer login status:", login_resp.status_code)
assert login_resp.status_code == 200

export_resp = client.get("/api/students/export/csv", cookies=login_resp.cookies)
print("Officer Export status:", export_resp.status_code)
print("Content-type:", export_resp.headers.get("content-type"))
print("First 200 chars of Student Roster CSV:\n", export_resp.text[:200])
assert export_resp.status_code == 200
assert "roll_no,name,email,branch,program,cgpa" in export_resp.text

# Test Student Login & Personal CSV Export with code 123456
student_login_resp = client.post("/api/auth/student-login", json={"roll_no": "BT210001", "code": "123456"})
print("Student login status:", student_login_resp.status_code)
assert student_login_resp.status_code == 200

student_csv_resp = client.get("/api/portal/status-sheet-csv", cookies=student_login_resp.cookies)
print("Student CSV export status:", student_csv_resp.status_code)
print("Content-type:", student_csv_resp.headers.get("content-type"))
print("First 300 chars of Student Status CSV:\n", student_csv_resp.text[:300])
assert student_csv_resp.status_code == 200
assert "CANDIDATE PLACEMENT STATUS PROFILE" in student_csv_resp.text
assert "BT210001" in student_csv_resp.text

print("\nALL BACKEND CSV EXPORT TESTS PASSED SUCCESSFULLY!")
