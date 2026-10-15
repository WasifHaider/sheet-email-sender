from typing import Optional

from fastapi import APIRouter, Depends

from ..db import get_supabase

router = APIRouter()


@router.get("/jobs")
def list_jobs(
    status: Optional[str] = None,
    batch_id: Optional[str] = None,
    db=Depends(get_supabase),
):
    query = db.table("email_jobs").select("*")
    if status:
        query = query.eq("status", status)
    if batch_id:
        query = query.eq("batch_id", batch_id)
    result = query.order("created_at", desc=True).execute()
    return {"jobs": result.data}
