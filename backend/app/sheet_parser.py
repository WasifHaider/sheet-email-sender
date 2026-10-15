from typing import BinaryIO, Optional
import pandas as pd

REQUIRED_COLUMNS = ["To", "From", "Subject", "Email Content"]


class SheetParseError(Exception):
    pass


def parse_sheet(file_obj: BinaryIO, filename: str) -> list[dict]:
    if filename.lower().endswith(".csv"):
        df = pd.read_csv(file_obj)
    else:
        df = pd.read_excel(file_obj)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise SheetParseError(f"Missing required columns: {', '.join(missing)}")

    rows = []
    for _, row in df.iterrows():
        rows.append(
            {
                "to_email": str(row["To"]).strip(),
                "from_email": str(row["From"]).strip(),
                "subject": str(row["Subject"]).strip(),
                "content": str(row["Email Content"]),
                "cc": _clean_optional(row.get("CC")),
                "attachment_filename": _clean_optional(row.get("Attachment")),
                "send_date": _parse_date(row.get("Date")),
                "send_time": _parse_time(row.get("Time")),
            }
        )
    return rows


def _clean_optional(value) -> Optional[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None


def _parse_date(value) -> Optional[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return pd.to_datetime(value).date().isoformat()


def _parse_time(value) -> Optional[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if hasattr(value, "isoformat") and not isinstance(value, str):
        return value.isoformat()
    return pd.to_datetime(value).time().isoformat()
