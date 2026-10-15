from datetime import datetime

from fastapi import APIRouter, Depends

from ..auth import get_current_user
from ..db import get_supabase

router = APIRouter()


@router.get("/batches/{batch_id}")
def get_batch(batch_id: str, db=Depends(get_supabase), user: dict = Depends(get_current_user)):
    result = (
        db.table("email_jobs")
        .select("*")
        .eq("batch_id", batch_id)
        .eq("user_id", user["id"])
        .execute()
    )
    return {"rows": result.data}


@router.post("/batches/{batch_id}/confirm")
def confirm_batch(batch_id: str, db=Depends(get_supabase), user: dict = Depends(get_current_user)):
    rows = (
        db.table("email_jobs")
        .select("*")
        .eq("batch_id", batch_id)
        .eq("user_id", user["id"])
        .execute()
        .data
    )
    now = datetime.now()

    for row in rows:
        send_date = row.get("send_date")
        if not send_date:
            new_status = "queued"
        else:
            send_time = row.get("send_time") or "00:00:00"
            scheduled_at = datetime.fromisoformat(f"{send_date}T{send_time}")
            new_status = "queued" if scheduled_at <= now else "scheduled"
        db.table("email_jobs").update({"status": new_status}).eq("id", row["id"]).execute()

    return {"batch_id": batch_id, "status": "confirmed"}
