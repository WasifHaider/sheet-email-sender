from typing import Optional

from fastapi import APIRouter, Depends

from ..auth import get_current_user
from ..db import get_supabase

router = APIRouter()


@router.get("/jobs")
def list_jobs(
    status: Optional[str] = None,
    batch_id: Optional[str] = None,
    db=Depends(get_supabase),
    user: dict = Depends(get_current_user),
):
    query = db.table("email_jobs").select("*").eq("user_id", user["id"])
    if status:
        query = query.eq("status", status)
    if batch_id:
        query = query.eq("batch_id", batch_id)
    result = query.order("created_at", desc=True).execute()
    return {"jobs": result.data}
