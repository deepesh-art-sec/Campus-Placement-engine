"""
Tests for Messages & Exports:
Verifies official candidate communication, LAN broadcast, template generation,
and company/schedule/student master exports in XLSX and CSV.
"""

from __future__ import annotations

import io
import openpyxl
from starlette.testclient import TestClient

from backend.app.api.main import app


def test_messages_templates_and_broadcast() -> None:
    client = TestClient(app)
    # 1. Login as officer
    login_res = client.post("/api/auth/login", json={"username": "officer", "password": "officer123"})
    assert login_res.status_code == 200
    csrf = login_res.json().get("csrf_token") or client.cookies.get("csrf_token")

    # 2. Get message templates
    tpl_res = client.get("/api/messages/templates")
    assert tpl_res.status_code == 200
    templates = tpl_res.json()
    assert len(templates) >= 4
    template_ids = [t["id"] for t in templates]
    assert "interview_call" in template_ids
    assert "shortlist_notice" in template_ids

    # 3. Broadcast to shortlisted candidates of drv_campus_partner
    bcast_res = client.post(
        "/api/messages/broadcast",
        json={
            "title": "Interview Call — Campus Partner",
            "message": "Dear {student_name} ({roll_no}), report to {venue} for {company_name}.",
            "target": "drive_shortlist",
            "drive_id": "drv_campus_partner",
            "category": "interview_call",
        },
        headers={"X-CSRF-Token": csrf} if csrf else {},
    )
    assert bcast_res.status_code == 200
    data = bcast_res.json()
    assert data["status"] == "success"
    assert data["recipient_count"] > 0

    # 4. Check broadcast history
    hist_res = client.get("/api/messages/broadcast-history")
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history) > 0
    assert any("Campus Partner" in h["title"] for h in history)

    # 5. Check candidate slips data
    passes_res = client.get("/api/messages/candidate-passes/drv_campus_partner")
    assert passes_res.status_code == 200
    passes_data = passes_res.json()
    assert passes_data["total_candidates"] > 0
    assert len(passes_data["passes"]) > 0


def test_operational_file_exports() -> None:
    client = TestClient(app)
    login_res = client.post("/api/auth/login", json={"username": "officer", "password": "officer123"})
    assert login_res.status_code == 200

    # 1. Company shortlist XLSX & CSV
    r_xlsx = client.get("/api/exports/company/drv_campus_partner?as_csv=false")
    assert r_xlsx.status_code == 200
    assert "application/vnd.openxmlformats" in r_xlsx.headers["content-type"]
    wb = openpyxl.load_workbook(io.BytesIO(r_xlsx.content))
    assert len(wb.sheetnames) >= 1

    r_csv = client.get("/api/exports/company/drv_campus_partner?as_csv=true")
    assert r_csv.status_code == 200
    assert "text/csv" in r_csv.headers["content-type"]
    assert len(r_csv.text.splitlines()) > 5

    # 2. Singular alias /api/export/company
    r_alias_xlsx = client.get("/api/export/company/drv_campus_partner")
    assert r_alias_xlsx.status_code == 200
    r_alias_csv = client.get("/api/export/company/drv_campus_partner?format=csv")
    assert r_alias_csv.status_code == 200

    # 3. Schedule export XLSX & CSV
    r_sched_xlsx = client.get("/api/exports/schedule/drv_campus_partner")
    assert r_sched_xlsx.status_code == 200
    r_sched_csv = client.get("/api/exports/schedule/drv_campus_partner?format=csv")
    assert r_sched_csv.status_code == 200
    assert "text/csv" in r_sched_csv.headers["content-type"]

    # 4. Master student CSV export
    r_stu = client.get("/api/exports/students/csv")
    assert r_stu.status_code == 200
    assert len(r_stu.text.splitlines()) > 100
