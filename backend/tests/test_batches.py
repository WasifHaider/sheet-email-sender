from fastapi.testclient import TestClient
from app.main import app
from app.db import get_supabase
from app.auth import get_current_user

FAKE_USER = {"id": "user-1", "email": "me@x.com"}
OTHER_USER = {"id": "user-2", "email": "other@x.com"}


def test_get_batch_returns_only_the_caller_s_rows(fake_db):
    fake_db.table("email_jobs").insert(
        [{"batch_id": "b1", "to_email": "a@x.com", "status": "pending_review", "user_id": "user-1"}]
    ).execute()
    fake_db.table("email_jobs").insert(
        [{"batch_id": "b1", "to_email": "z@x.com", "status": "pending_review", "user_id": "user-2"}]
    ).execute()

    app.dependency_overrides[get_supabase] = lambda: fake_db
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    client = TestClient(app)

    response = client.get("/batches/b1")

    assert response.status_code == 200
    rows = response.json()["rows"]
    assert len(rows) == 1
    assert rows[0]["to_email"] == "a@x.com"

    app.dependency_overrides.clear()


def test_batches_require_authentication(fake_db):
    app.dependency_overrides[get_supabase] = lambda: fake_db
    client = TestClient(app)

    response = client.get("/batches/b1")

    assert response.status_code == 401

    app.dependency_overrides.clear()


def test_confirm_batch_queues_rows_without_date(fake_db):
    fake_db.table("email_jobs").insert(
        [{"batch_id": "b1", "to_email": "a@x.com", "status": "pending_review",
          "send_date": None, "send_time": None, "user_id": "user-1"}]
    ).execute()

    app.dependency_overrides[get_supabase] = lambda: fake_db
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    client = TestClient(app)

    response = client.post("/batches/b1/confirm")

    assert response.status_code == 200
    rows = fake_db.table("email_jobs").select("*").eq("batch_id", "b1").execute().data
    assert rows[0]["status"] == "queued"

    app.dependency_overrides.clear()


def test_confirm_batch_schedules_future_rows(fake_db):
    fake_db.table("email_jobs").insert(
        [{"batch_id": "b2", "to_email": "a@x.com", "status": "pending_review",
          "send_date": "2099-01-01", "send_time": "09:00:00", "user_id": "user-1"}]
    ).execute()

    app.dependency_overrides[get_supabase] = lambda: fake_db
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    client = TestClient(app)

    client.post("/batches/b2/confirm")

    rows = fake_db.table("email_jobs").select("*").eq("batch_id", "b2").execute().data
    assert rows[0]["status"] == "scheduled"

    app.dependency_overrides.clear()


def test_confirm_batch_does_not_touch_another_user_s_rows(fake_db):
    fake_db.table("email_jobs").insert(
        [{"batch_id": "b3", "to_email": "z@x.com", "status": "pending_review",
          "send_date": None, "send_time": None, "user_id": "user-2"}]
    ).execute()

    app.dependency_overrides[get_supabase] = lambda: fake_db
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    client = TestClient(app)

    client.post("/batches/b3/confirm")

    rows = fake_db.table("email_jobs").select("*").eq("batch_id", "b3").execute().data
    assert rows[0]["status"] == "pending_review"

    app.dependency_overrides.clear()
