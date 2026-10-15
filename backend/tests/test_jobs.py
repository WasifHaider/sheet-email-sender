from fastapi.testclient import TestClient
from app.main import app
from app.db import get_supabase
from app.auth import get_current_user

FAKE_USER = {"id": "user-1", "email": "me@x.com"}


def test_list_jobs_filters_by_status_and_owner(fake_db):
    fake_db.table("email_jobs").insert(
        [
            {"batch_id": "b1", "to_email": "a@x.com", "status": "sent", "user_id": "user-1"},
            {"batch_id": "b1", "to_email": "b@x.com", "status": "failed", "user_id": "user-1"},
            {"batch_id": "b1", "to_email": "z@x.com", "status": "failed", "user_id": "user-2"},
        ]
    ).execute()

    app.dependency_overrides[get_supabase] = lambda: fake_db
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    client = TestClient(app)

    response = client.get("/jobs", params={"status": "failed"})

    assert response.status_code == 200
    jobs = response.json()["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["to_email"] == "b@x.com"

    app.dependency_overrides.clear()


def test_jobs_require_authentication(fake_db):
    app.dependency_overrides[get_supabase] = lambda: fake_db
    client = TestClient(app)

    response = client.get("/jobs")

    assert response.status_code == 401

    app.dependency_overrides.clear()
