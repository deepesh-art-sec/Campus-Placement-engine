"""
Comprehensive Test Suite for MongoDB Database Storage & Synchronization.
Tests connection diagnostics, URI masking, NoSQL schema transformation,
and full synchronization of collegiate placement data.
"""

from unittest.mock import patch
import mongomock
import pytest
from fastapi.testclient import TestClient

from backend.app.api.main import app
from backend.app.storage.database import SessionLocal
from backend.app.storage.mongodb import (
    MongoSyncService,
    get_configured_db_name,
    get_configured_uri,
    get_mongodb_status,
    mask_mongo_uri,
    ping_mongodb,
)


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def auth_headers(client):
    res = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200
    csrf = res.json().get("csrf_token")
    return {"X-CSRF-Token": csrf}


def test_mask_mongo_uri():
    """Verifies that credentials in MongoDB connection strings are properly masked."""
    assert mask_mongo_uri("mongodb://localhost:27017") == "mongodb://localhost:27017"
    assert (
        mask_mongo_uri("mongodb://admin:secretPass123@192.168.1.50:27017/placement_engine")
        == "mongodb://admin:****@192.168.1.50:27017/placement_engine"
    )
    assert (
        mask_mongo_uri("mongodb+srv://placement_admin:SuperSecretKey@cluster0.abcde.mongodb.net/prod")
        == "mongodb+srv://placement_admin:****@cluster0.abcde.mongodb.net/prod"
    )
    assert mask_mongo_uri("") == ""


def test_mongodb_status_structure():
    """Verifies that get_mongodb_status returns consistent metadata schema."""
    status = get_mongodb_status()
    assert isinstance(status, dict)
    assert "configured_uri" in status
    assert "database" in status
    assert "connected" in status
    assert "collections" in status
    assert "total_documents" in status


def test_mongodb_ping_diagnostic():
    """Verifies ping_mongodb diagnostics output."""
    res = ping_mongodb()
    assert isinstance(res, dict)
    assert "connected" in res
    assert "uri" in res


def test_mongodb_api_status_and_ping(client, auth_headers):
    """Verifies GET /api/mongodb/status and /api/mongodb/ping return 200."""
    status_res = client.get("/api/mongodb/status", headers=auth_headers)
    assert status_res.status_code == 200
    s_data = status_res.json()
    assert "configured_uri" in s_data
    assert "database" in s_data

    ping_res = client.get("/api/mongodb/ping", headers=auth_headers)
    assert ping_res.status_code == 200
    p_data = ping_res.json()
    assert "connected" in p_data


def test_mongodb_sync_full_mocked():
    mock_mongo_client = mongomock.MongoClient()
    mock_db = mock_mongo_client["placement_engine"]

    with patch("backend.app.storage.mongodb.get_mongo_db", return_value=mock_db), \
         patch("backend.app.storage.mongodb.get_mongo_client", return_value=mock_mongo_client), \
         patch("backend.app.api.routes.mongodb_routes.get_mongo_db", return_value=mock_db), \
         patch("backend.app.api.routes.mongodb_routes.get_mongo_client", return_value=mock_mongo_client):

        db_session = SessionLocal()
        try:
            report = MongoSyncService.sync_all(db_session)
            assert report["status"] == "success"
            assert report["total_documents"] > 0
            assert "students" in report["counts"]
            assert "drives" in report["counts"]
            assert "companies" in report["counts"]

            # Inspect documents written into mongomock
            students_count = mock_db.students.count_documents({})
            assert students_count > 0
            sample_student = mock_db.students.find_one()
            assert sample_student is not None
            assert "roll_no" in sample_student
            assert "cgpa" in sample_student
            assert "backlogs" in sample_student
            assert isinstance(sample_student["backlogs"], list)

            drives_count = mock_db.drives.count_documents({})
            assert drives_count > 0
            sample_drive = mock_db.drives.find_one()
            assert sample_drive is not None
            assert "company_name" in sample_drive

        finally:
            db_session.close()


def test_mongodb_api_sync_and_collections(client, auth_headers):
    """Verifies POST /api/mongodb/sync, GET /api/mongodb/collections, and document inspector."""
    mock_mongo_client = mongomock.MongoClient()
    mock_db = mock_mongo_client["placement_engine"]

    with patch("backend.app.storage.mongodb.get_mongo_db", return_value=mock_db), \
         patch("backend.app.storage.mongodb.get_mongo_client", return_value=mock_mongo_client), \
         patch("backend.app.api.routes.mongodb_routes.get_mongo_db", return_value=mock_db), \
         patch("backend.app.api.routes.mongodb_routes.get_mongo_client", return_value=mock_mongo_client):

        # Trigger sync via API
        sync_res = client.post("/api/mongodb/sync", headers=auth_headers)
        assert sync_res.status_code == 200
        sync_data = sync_res.json()
        assert sync_data["status"] == "success"
        assert sync_data["total_documents"] > 0

        # Query collections endpoint
        colls_res = client.get("/api/mongodb/collections", headers=auth_headers)
        assert colls_res.status_code == 200
        colls_data = colls_res.json()
        assert "collections" in colls_data
        assert "students" in colls_data["collections"]

        # Inspect specific collection
        inspect_res = client.get("/api/mongodb/collections/students?limit=5", headers=auth_headers)
        assert inspect_res.status_code == 200
        inspect_data = inspect_res.json()
        assert inspect_data["collection"] == "students"
        assert len(inspect_data["documents"]) > 0
        assert "roll_no" in inspect_data["documents"][0]
