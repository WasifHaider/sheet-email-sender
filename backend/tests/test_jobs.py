from fastapi.testclient import TestClient
from app.main import app
from app.db import get_supabase


def test_list_jobs_filters_by_status(fake_db):
    fake_db.table("email_jobs").insert(
        [
            {"batch_id": "b1", "to_email": "a@x.com", "status": "sent"},
            {"batch_id": "b1", "to_email": "b@x.com", "status": "failed"},
        ]
    ).execute()

    app.dependency_overrides[get_supabase] = lambda: fake_db
    client = TestClient(app)

    response = client.get("/jobs", params={"status": "failed"})

    assert response.status_code == 200
    jobs = response.json()["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["to_email"] == "b@x.com"

    app.dependency_overrides.clear()
