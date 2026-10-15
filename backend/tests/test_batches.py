from fastapi.testclient import TestClient
from app.main import app
from app.db import get_supabase


def test_get_batch_returns_its_rows(fake_db):
    fake_db.table("email_jobs").insert(
        [{"batch_id": "b1", "to_email": "a@x.com", "status": "pending_review"}]
    ).execute()
    fake_db.table("email_jobs").insert(
        [{"batch_id": "b2", "to_email": "z@x.com", "status": "pending_review"}]
    ).execute()

    app.dependency_overrides[get_supabase] = lambda: fake_db
    client = TestClient(app)

    response = client.get("/batches/b1")

    assert response.status_code == 200
    rows = response.json()["rows"]
    assert len(rows) == 1
    assert rows[0]["to_email"] == "a@x.com"

    app.dependency_overrides.clear()
