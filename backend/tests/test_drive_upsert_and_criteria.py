import json
import pytest
from collections.abc import Generator
from fastapi.testclient import TestClient
from sqlalchemy import select, delete
from backend.app.api.main import app, seed_default_accounts
from backend.app.storage.database import SessionLocal
from backend.app.storage.models.entities import DriveModel, DriveRequirementVersionModel, CompanyModel

@pytest.fixture
def officer_client() -> Generator[tuple[TestClient, dict[str, str]], None, None]:
    seed_default_accounts()
    with TestClient(app) as c:
        login_res = c.post("/api/auth/login", json={"username": "officer", "password": "officer123"})
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        csrf_token = login_res.json().get("csrf_token", "")
        headers = {"X-CSRF-Token": csrf_token}
        yield c, headers

def test_drive_upsert_and_criteria_persistence(officer_client):
    client, headers = officer_client
    db = SessionLocal()

    test_company = "Apex Innovations TestCorp"
    try:
        # 1. First creation of drive
        create_payload = {
            "company_name": test_company,
            "drive_date": "2026-11-25",
            "mode": "on_campus",
            "status": "published",
            "ctc_lpa": 14.5,
            "min_cgpa": 7.5,
            "min_tenth_percentage": 70.0,
            "min_twelfth_percentage": 70.0,
            "allowed_branches": ["CSE", "IT"],
            "max_active_backlogs": 0,
            "max_history_backlogs": 1,
            "max_gap_years": 1,
            "min_diploma_percentage": 65.0,
            "allow_gap_during_degree": False,
        }
        res1 = client.post("/api/drives", json=create_payload, headers=headers)
        assert res1.status_code in (200, 201), res1.text
        drive_id = res1.json()["id"]

        # Verify drive exists in DB
        d1 = db.execute(select(DriveModel).where(DriveModel.id == drive_id)).scalar_one()
        assert d1.company_name == test_company
        assert d1.ctc_lpa == 14.5

        # Verify requirement exists
        req1 = db.execute(
            select(DriveRequirementVersionModel)
            .where(DriveRequirementVersionModel.drive_id == drive_id)
            .order_by(DriveRequirementVersionModel.version_number.desc())
        ).scalars().first()
        assert req1 is not None
        assert req1.min_cgpa == 7.5
        assert "CSE" in req1.allowed_branches_json

        # 2. Idempotent Upsert via POST (same company, different criteria)
        # Should NOT raise 409 and should NOT create a duplicate drive
        update_payload = {
            "company_name": test_company,
            "drive_date": "2026-11-28",
            "mode": "hybrid",
            "status": "published",
            "ctc_lpa": 16.0,
            "min_cgpa": 8.2,
            "min_tenth_percentage": 75.0,
            "min_twelfth_percentage": 75.0,
            "allowed_branches": ["CSE", "IT", "ECE"],
            "max_active_backlogs": 0,
            "max_history_backlogs": 0,
            "max_gap_years": 0,
            "min_diploma_percentage": 70.0,
            "allow_gap_during_degree": False,
        }
        res2 = client.post("/api/drives", json=update_payload, headers=headers)
        assert res2.status_code in (200, 201), res2.text
        data2 = res2.json()
        assert data2["id"] == drive_id
        assert "updated" in data2["message"].lower()

        # Check deduplication: exactly 1 drive for test_company
        drives = db.execute(
            select(DriveModel).where(DriveModel.company_name == test_company)
        ).scalars().all()
        assert len(drives) == 1

        # Check updated criteria in DB
        db.expire_all()
        req2 = db.execute(
            select(DriveRequirementVersionModel)
            .where(DriveRequirementVersionModel.drive_id == drive_id)
            .order_by(DriveRequirementVersionModel.version_number.desc())
        ).scalars().first()
        assert req2.min_cgpa == 8.2
        assert "ECE" in req2.allowed_branches_json
        assert req2.min_tenth_percentage == 75.0

        # 3. PUT /api/drives/{drive_id} update criteria
        put_payload = {
            "company_name": test_company,
            "drive_date": "2026-12-01",
            "mode": "on_campus",
            "status": "published",
            "ctc_lpa": 18.0,
            "min_cgpa": 8.75,
            "min_tenth_percentage": 80.0,
            "min_twelfth_percentage": 80.0,
            "allowed_branches": ["CSE"],
            "max_active_backlogs": 0,
            "max_history_backlogs": 0,
            "max_gap_years": 0,
            "min_diploma_percentage": 75.0,
            "allow_gap_during_degree": False,
        }
        res3 = client.put(f"/api/drives/{drive_id}", json=put_payload, headers=headers)
        assert res3.status_code == 200, res3.text

        # Verify criteria saved through PUT
        db.expire_all()
        d3 = db.execute(select(DriveModel).where(DriveModel.id == drive_id)).scalar_one()
        assert d3.ctc_lpa == 18.0
        assert str(d3.drive_date) == "2026-12-01"

        req3 = db.execute(
            select(DriveRequirementVersionModel)
            .where(DriveRequirementVersionModel.drive_id == drive_id)
            .order_by(DriveRequirementVersionModel.version_number.desc())
        ).scalars().first()
        assert req3.min_cgpa == 8.75
        assert req3.min_tenth_percentage == 80.0
        assert "CSE" in req3.allowed_branches_json

    finally:
        # Teardown test data cleanly
        db.execute(delete(DriveRequirementVersionModel).where(DriveRequirementVersionModel.drive_id.in_(
            select(DriveModel.id).where(DriveModel.company_name == test_company)
        )))
        db.execute(delete(DriveModel).where(DriveModel.company_name == test_company))
        db.execute(delete(CompanyModel).where(CompanyModel.name == test_company))
        db.commit()
        db.close()
