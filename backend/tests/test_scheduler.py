from datetime import datetime, timedelta

from app.scheduler import due_jobs, process_job


def test_due_jobs_includes_queued_and_past_scheduled(fake_db):
    past_date = (datetime.now() - timedelta(days=1)).date().isoformat()
    future_date = (datetime.now() + timedelta(days=1)).date().isoformat()

    fake_db.table("email_jobs").insert(
        [
            {"batch_id": "b1", "status": "queued"},
            {"batch_id": "b1", "status": "scheduled", "send_date": past_date, "send_time": "00:00:00"},
            {"batch_id": "b1", "status": "scheduled", "send_date": future_date, "send_time": "00:00:00"},
            {"batch_id": "b1", "status": "sent"},
        ]
    ).execute()

    due = due_jobs(fake_db)

    assert len(due) == 2
    assert all(job["status"] in ("queued", "scheduled") for job in due)


def test_process_job_marks_sent_on_success(fake_db, monkeypatch):
    fake_db.table("email_jobs").insert(
        [{"id": "job-1", "batch_id": "b1", "to_email": "a@x.com", "from_email": "b@x.com",
          "cc": None, "subject": "Hi", "content": "Body", "attachment_filename": None,
          "status": "queued"}]
    ).execute()
    job = fake_db.table("email_jobs").select("*").eq("id", "job-1").execute().data[0]

    monkeypatch.setattr("app.scheduler.send_message", lambda msg: None)

    process_job(fake_db, job)

    updated = fake_db.table("email_jobs").select("*").eq("id", "job-1").execute().data[0]
    assert updated["status"] == "sent"
    assert updated["sent_at"] is not None


def test_process_job_marks_failed_on_exception(fake_db, monkeypatch):
    fake_db.table("email_jobs").insert(
        [{"id": "job-2", "batch_id": "b1", "to_email": "a@x.com", "from_email": "b@x.com",
          "cc": None, "subject": "Hi", "content": "Body", "attachment_filename": None,
          "status": "queued"}]
    ).execute()
    job = fake_db.table("email_jobs").select("*").eq("id", "job-2").execute().data[0]

    def _raise(msg):
        raise RuntimeError("smtp down")

    monkeypatch.setattr("app.scheduler.send_message", _raise)

    process_job(fake_db, job)

    updated = fake_db.table("email_jobs").select("*").eq("id", "job-2").execute().data[0]
    assert updated["status"] == "failed"
    assert "smtp down" in updated["error_message"]
