"""
Tests for 25 Real-Format Drive Announcements Library API.
"""

from __future__ import annotations

from collections.abc import Generator
import pytest
from fastapi.testclient import TestClient

from backend.app.api.main import app, seed_default_accounts


@pytest.fixture
def auth_client() -> Generator[tuple[TestClient, str], None, None]:
    seed_default_accounts()
    with TestClient(app) as client:
        # Authenticate as officer
        res = client.post("/api/auth/login", json={"username": "officer", "password": "officer123"})
        assert res.status_code == 200
        csrf = res.json()["csrf_token"]
        yield client, csrf


def test_list_all_25_announcements(auth_client: tuple[TestClient, str]):
    """Verifies that all 25 real-format drive announcements are loaded with full metadata."""
    client, csrf = auth_client
    response = client.get("/api/announcements")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 25

    formats = {item["format"] for item in data}
    assert "EML" in formats
    assert "PDF" in formats
    assert "DOCX" in formats
    assert "TXT" in formats

    # Verify first item contains expected fields
    first = data[0]
    assert "filename" in first
    assert "company_name" in first
    assert "format" in first
    assert "ctc_lpa" in first
    assert "cgpa_min" in first
    assert "drive_date" in first
    assert "download_url" in first
    assert len(first["snippet"]) > 0


def test_filter_announcements_by_format(auth_client: tuple[TestClient, str]):
    """Verifies format filtering for EML, PDF, DOCX, and TXT."""
    client, csrf = auth_client
    for fmt in ["EML", "PDF", "DOCX", "TXT"]:
        res = client.get(f"/api/announcements?format_filter={fmt}")
        assert res.status_code == 200
        items = res.json()
        assert len(items) > 0
        assert all(it["format"] == fmt for it in items)


def test_get_announcement_details_and_download(auth_client: tuple[TestClient, str]):
    """Verifies fetching full text and raw file download."""
    client, csrf = auth_client
    list_res = client.get("/api/announcements")
    assert list_res.status_code == 200
    first_fn = list_res.json()[0]["filename"]

    # Details
    detail_res = client.get(f"/api/announcements/{first_fn}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["filename"] == first_fn
    assert "full_text" in detail
    assert len(detail["full_text"]) > 0
    assert "ground_truth" in detail

    # Download
    dl_res = client.get(f"/api/announcements/{first_fn}/download")
    assert dl_res.status_code == 200
    assert len(dl_res.content) > 0


def test_instant_drive_creation_from_announcement(auth_client: tuple[TestClient, str]):
    """Verifies 1-click converting an announcement to an active recruitment drive."""
    client, csrf = auth_client
    list_res = client.get("/api/announcements")
    assert list_res.status_code == 200
    first_fn = list_res.json()[0]["filename"]

    create_res = client.post(
        f"/api/announcements/{first_fn}/instant-drive",
        headers={"X-CSRF-Token": csrf},
    )
    assert create_res.status_code == 200
    data = create_res.json()
    assert data["status"] in ("created", "exists", "success")
    assert "drive_id" in data
    assert "company_name" in data
    assert "ctc_lpa" in data
