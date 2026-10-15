from fastapi import APIRouter, Depends

from ..db import get_supabase

router = APIRouter()


@router.get("/batches/{batch_id}")
def get_batch(batch_id: str, db=Depends(get_supabase)):
    result = db.table("email_jobs").select("*").eq("batch_id", batch_id).execute()
    return {"rows": result.data}
