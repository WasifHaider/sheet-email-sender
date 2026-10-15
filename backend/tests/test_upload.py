import io
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_supabase
from app.auth import get_current_user

FAKE_USER = {"id": "user-1", "email": "me@x.com"}


def test_upload_parses_and_stores_rows(fake_db):
    app.dependency_overrides[get_supabase] = lambda: fake_db
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    client = TestClient(app)

    csv_text = "To,Subject,Email Content\na@x.com,Hello,Hi there\n"
    files = {"sheet": ("sheet.csv", io.BytesIO(csv_text.encode()), "text/csv")}
    response = client.post("/upload", files=files)

    assert response.status_code == 200
    body = response.json()
    assert "batch_id" in body
    assert len(body["rows"]) == 1
    row = body["rows"][0]
    assert row["status"] == "pending_review"
    assert row["to_email"] == "a@x.com"
    assert row["user_id"] == "user-1"
    assert row["from_email"] == "me@x.com"

    app.dependency_overrides.clear()


def test_upload_requires_authentication(fake_db):
    app.dependency_overrides[get_supabase] = lambda: fake_db
    client = TestClient(app)

    csv_text = "To,Subject,Email Content\na@x.com,Hello,Hi there\n"
    files = {"sheet": ("sheet.csv", io.BytesIO(csv_text.encode()), "text/csv")}
    response = client.post("/upload", files=files)

    assert response.status_code == 401

    app.dependency_overrides.clear()


def test_upload_auto_links_single_attachment_to_blank_rows(fake_db):
    app.dependency_overrides[get_supabase] = lambda: fake_db
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    client = TestClient(app)

    csv_text = "To,Subject,Email Content\na@x.com,Hello,Hi there\n"
    files = {
        "sheet": ("sheet.csv", io.BytesIO(csv_text.encode()), "text/csv"),
        "attachments": ("report.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf"),
    }
    response = client.post("/upload", files=files)

    assert response.status_code == 200
    assert response.json()["rows"][0]["attachment_filename"] == "report.pdf"

    app.dependency_overrides.clear()


def test_upload_does_not_auto_link_when_multiple_attachments(fake_db):
    app.dependency_overrides[get_supabase] = lambda: fake_db
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    client = TestClient(app)

    csv_text = "To,Subject,Email Content\na@x.com,Hello,Hi there\n"
    files = [
        ("sheet", ("sheet.csv", io.BytesIO(csv_text.encode()), "text/csv")),
        ("attachments", ("report.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")),
        ("attachments", ("notes.txt", io.BytesIO(b"hi"), "text/plain")),
    ]
    response = client.post("/upload", files=files)

    assert response.status_code == 200
    assert response.json()["rows"][0]["attachment_filename"] is None

    app.dependency_overrides.clear()
