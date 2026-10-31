"""
Test Attendance Marking, Cross-Dashboard Synchronization, Connected Notifications, and Exports.
Verifies that:
1. Officers and Coordinators can both mark and inspect attendance.
2. Changes made by either role are immediately reflected.
3. Connected announcements from all dashboards appear in Coordinator notifications.
4. Attendance CSV, Schedule CSV, and Student Roster CSV exports generate valid attachments.
"""

import json
import pytest
from fastapi.testclient import TestClient
from backend.app.api.main import app, seed_default_accounts
from backend.app.storage.database import SessionLocal
from backend.app.storage.models.entities import (
    DriveModel,
    DriveAttendanceModel,
    StudentModel,
    NotificationModel,
    CompanyModel,
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Provides authentication headers for officer and coordinator."""
    # Login as Officer
    res_off = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert res_off.status_code == 200
    off_csrf = res_off.json().get("csrf_token")

    # Login as Coordinator
    res_coord = client.post("/api/auth/login", json={"username": "coordinator", "password": "coord123"})
    assert res_coord.status_code == 200
    coord_csrf = res_coord.json().get("csrf_token")

    return {
        "officer": {"X-CSRF-Token": off_csrf},
        "coordinator": {"X-CSRF-Token": coord_csrf},
    }


def test_attendance_bidirectional_sync(client):
    # 1. Login as Officer
    res_off = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert res_off.status_code == 200
    off_csrf = res_off.json().get("csrf_token")

    # 2. Get active drives
    drives_res = client.get("/api/drives")
    assert drives_res.status_code == 200
    drives = drives_res.json()
    assert len(drives) > 0
    test_drive = drives[0]
    drive_id = test_drive["id"]

    # 3. Fetch attendance as Officer
    att_res = client.get(f"/api/coordinator/attendance/{drive_id}", headers={"X-CSRF-Token": off_csrf})
    assert att_res.status_code == 200
    att_data = att_res.json()
    assert "rooms" in att_data
    assert att_data["drive_id"] == drive_id

    # Find a candidate to test with
    rooms = att_data["rooms"]
    first_room = next(iter(rooms.keys()))
    candidates = rooms[first_room]
    assert len(candidates) > 0
    test_student = candidates[0]
    student_id = test_student["student_id"]

    # 4. Officer marks candidate as "present"
    mark_res = client.post(
        "/api/coordinator/attendance/mark",
        json={
            "drive_id": drive_id,
            "student_id": student_id,
            "room_name": first_room,
            "status": "present",
            "notes": "Verified by Officer Desk",
        },
        headers={"X-CSRF-Token": off_csrf},
    )
    assert mark_res.status_code == 200

    # 5. Login as Coordinator
    res_coord = client.post("/api/auth/login", json={"username": "coordinator", "password": "coord123"})
    assert res_coord.status_code == 200
    coord_csrf = res_coord.json().get("csrf_token")

    # 6. Coordinator immediately inspects attendance -> Officer's edit is instantly visible!
    coord_att_res = client.get(f"/api/coordinator/attendance/{drive_id}", headers={"X-CSRF-Token": coord_csrf})
    assert coord_att_res.status_code == 200
    coord_att_data = coord_att_res.json()
    coord_candidate = next(c for c in coord_att_data["rooms"][first_room] if c["student_id"] == student_id)
    assert coord_candidate["attendance_status"] == "present"
    assert coord_candidate["notes"] == "Verified by Officer Desk"

    # 7. Coordinator updates status to "late"
    coord_mark_res = client.post(
        "/api/coordinator/attendance/mark",
        json={
            "drive_id": drive_id,
            "student_id": student_id,
            "room_name": first_room,
            "status": "late",
            "notes": "Arrived 10 mins late",
        },
        headers={"X-CSRF-Token": coord_csrf},
    )
    assert coord_mark_res.status_code == 200

    # 8. Re-login Officer and inspect -> Coordinator's edit is instantly visible to Officer!
    res_off2 = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert res_off2.status_code == 200
    off2_csrf = res_off2.json().get("csrf_token")

    officer_check_res = client.get(f"/api/coordinator/attendance/{drive_id}", headers={"X-CSRF-Token": off2_csrf})
    assert officer_check_res.status_code == 200
    off_candidate = next(c for c in officer_check_res.json()["rooms"][first_room] if c["student_id"] == student_id)
    assert off_candidate["attendance_status"] == "late"
    assert off_candidate["notes"] == "Arrived 10 mins late"


def test_attendance_bulk_mark(client):
    # Login as Coordinator
    res_coord = client.post("/api/auth/login", json={"username": "coordinator", "password": "coord123"})
    coord_csrf = res_coord.json().get("csrf_token")

    drives = client.get("/api/drives").json()
    drive_id = drives[0]["id"]
    att_data = client.get(f"/api/coordinator/attendance/{drive_id}", headers={"X-CSRF-Token": coord_csrf}).json()
    first_room = next(iter(att_data["rooms"].keys()))
    student_ids = [c["student_id"] for c in att_data["rooms"][first_room][:3]]

    bulk_res = client.post(
        "/api/coordinator/attendance/bulk",
        json={
            "drive_id": drive_id,
            "room_name": first_room,
            "status": "present",
            "student_ids": student_ids,
        },
        headers={"X-CSRF-Token": coord_csrf},
    )
    assert bulk_res.status_code == 200
    assert bulk_res.json()["count"] == len(student_ids)


def test_connected_announcements_in_notifications(client):
    # 1. Officer broadcasts an announcement to all
    res_off = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    off_csrf = res_off.json().get("csrf_token")

    broadcast_res = client.post(
        "/api/messages/broadcast",
        json={
            "title": "Placement Drive Instructions Circular",
            "message": "All students and coordinators must report to Auditorium 2 by 8:30 AM tomorrow.",
            "target": "all",
            "category": "announcement",
        },
        headers={"X-CSRF-Token": off_csrf},
    )
    assert broadcast_res.status_code == 200

    # 2. Coordinator retrieves notifications -> Announcement is visible in Coordinator Notifications!
    res_coord = client.post("/api/auth/login", json={"username": "coordinator", "password": "coord123"})
    coord_csrf = res_coord.json().get("csrf_token")

    notifs_res = client.get("/api/coordinator/notifications", headers={"X-CSRF-Token": coord_csrf})
    assert notifs_res.status_code == 200
    notifs = notifs_res.json()
    assert isinstance(notifs, list)

    # Check that broadcast/announcement is present
    announcement_titles = [n["title"] for n in notifs]
    assert any("Placement Drive Instructions Circular" in t or "Announcement" in t for t in announcement_titles)

    # Test marking a notification as read
    target_notif = notifs[0]
    read_res = client.post(
        f"/api/coordinator/notifications/{target_notif['id']}/read",
        headers={"X-CSRF-Token": coord_csrf},
    )
    assert read_res.status_code == 200


def test_working_reports_and_exports(client):
    # Login as Coordinator
    res_coord = client.post("/api/auth/login", json={"username": "coordinator", "password": "coord123"})
    coord_csrf = res_coord.json().get("csrf_token")

    drives = client.get("/api/drives").json()
    drive_id = drives[0]["id"]

    # 1. Export Attendance CSV
    att_csv_res = client.get(f"/api/exports/attendance/{drive_id}/csv", headers={"X-CSRF-Token": coord_csrf})
    assert att_csv_res.status_code == 200
    assert "text/csv" in att_csv_res.headers.get("Content-Type", "")
    assert "Roll Number" in att_csv_res.text
    assert "Attendance Status" in att_csv_res.text

    # 2. Export Student Master Roster CSV
    stu_csv_res = client.get("/api/exports/students/csv", headers={"X-CSRF-Token": coord_csrf})
    assert stu_csv_res.status_code == 200
    assert "text/csv" in stu_csv_res.headers.get("Content-Type", "")
    assert "Roll Number" in stu_csv_res.text
    assert "CGPA" in stu_csv_res.text

    # 3. Export Schedule CSV
    sch_csv_res = client.get(f"/api/exports/schedule/{drive_id}?as_csv=true", headers={"X-CSRF-Token": coord_csrf})
    assert sch_csv_res.status_code == 200
    assert "text/csv" in sch_csv_res.headers.get("Content-Type", "")
    assert "Candidate Roll No" in sch_csv_res.text

    # 4. Export Company Shortlist CSV
    comp_csv_res = client.get(f"/api/exports/company/{drive_id}?as_csv=true", headers={"X-CSRF-Token": coord_csrf})
    assert comp_csv_res.status_code == 200
    assert "text/csv" in comp_csv_res.headers.get("Content-Type", "")
