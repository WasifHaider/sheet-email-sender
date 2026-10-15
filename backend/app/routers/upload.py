import pathlib
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from ..db import get_supabase
from ..sheet_parser import SheetParseError, parse_sheet

router = APIRouter()
UPLOAD_DIR = pathlib.Path("uploads")


@router.post("/upload")
async def upload_sheet(
    sheet: UploadFile = File(...),
    attachments: list[UploadFile] = File(default=[]),
    db=Depends(get_supabase),
):
    try:
        rows = parse_sheet(sheet.file, sheet.filename)
    except SheetParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    batch_id = str(uuid.uuid4())
    batch_dir = UPLOAD_DIR / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    attachment_names = []
    for attachment in attachments:
        contents = await attachment.read()
        (batch_dir / attachment.filename).write_bytes(contents)
        attachment_names.append(attachment.filename)

    # If exactly one attachment was uploaded, auto-link it to any row that
    # didn't specify a filename in the sheet's Attachment column.
    fallback_attachment = attachment_names[0] if len(attachment_names) == 1 else None
    if fallback_attachment:
        for row in rows:
            if not row.get("attachment_filename"):
                row["attachment_filename"] = fallback_attachment

    records = [
        {**row, "batch_id": batch_id, "status": "pending_review"} for row in rows
    ]
    result = db.table("email_jobs").insert(records).execute()
    return {"batch_id": batch_id, "rows": result.data}
