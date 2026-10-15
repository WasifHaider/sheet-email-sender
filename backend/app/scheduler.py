import asyncio
import pathlib
from datetime import datetime

from .db import get_supabase
from .mailer import build_message, get_access_token, send_via_gmail_api

UPLOAD_DIR = pathlib.Path("uploads")
POLL_SECONDS = 60


def due_jobs(db) -> list[dict]:
    result = db.table("email_jobs").select("*").in_("status", ["queued", "scheduled"]).execute()
    now = datetime.now()
    due = []
    for job in result.data:
        if job["status"] == "queued":
            due.append(job)
            continue
        send_date = job.get("send_date")
        send_time = job.get("send_time") or "00:00:00"
        scheduled_at = datetime.fromisoformat(f"{send_date}T{send_time}")
        if scheduled_at <= now:
            due.append(job)
    return due


def process_job(db, job: dict) -> None:
    attachment_path = None
    if job.get("attachment_filename"):
        attachment_path = UPLOAD_DIR / job["batch_id"] / job["attachment_filename"]

    msg = build_message(job, attachment_path)
    try:
        owner = db.table("users").select("*").eq("id", job["user_id"]).execute().data[0]
        access_token = get_access_token(owner["refresh_token"])
        send_via_gmail_api(access_token, msg)
        update = {"status": "sent", "sent_at": datetime.now().isoformat()}
        if job.get("attachment_filename") and not (attachment_path and attachment_path.exists()):
            update["error_message"] = "Attachment file missing; sent without it"
        db.table("email_jobs").update(update).eq("id", job["id"]).execute()
    except Exception as exc:
        db.table("email_jobs").update(
            {"status": "failed", "error_message": str(exc)}
        ).eq("id", job["id"]).execute()


async def scheduler_loop(db_factory=get_supabase) -> None:
    while True:
        db = db_factory()
        for job in due_jobs(db):
            process_job(db, job)
        await asyncio.sleep(POLL_SECONDS)
