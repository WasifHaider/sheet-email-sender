import io
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_supabase


def test_upload_parses_and_stores_rows(fake_db):
    app.dependency_overrides[get_supabase] = lambda: fake_db
    client = TestClient(app)

    csv_text = (
        "To,From,Subject,Email Content\n"
        "a@x.com,b@x.com,Hello,Hi there\n"
    )
    files = {"sheet": ("sheet.csv", io.BytesIO(csv_text.encode()), "text/csv")}
    response = client.post("/upload", files=files)

    assert response.status_code == 200
    body = response.json()
    assert "batch_id" in body
    assert len(body["rows"]) == 1
    assert body["rows"][0]["status"] == "pending_review"
    assert body["rows"][0]["to_email"] == "a@x.com"

    app.dependency_overrides.clear()
