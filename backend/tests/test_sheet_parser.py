import io
import pytest
from app.sheet_parser import parse_sheet, SheetParseError


def _csv_bytes(text: str) -> io.BytesIO:
    return io.BytesIO(text.encode("utf-8"))


def test_parse_sheet_happy_path():
    csv_text = (
        "To,From,Subject,Email Content,CC,Attachment,Date,Time\n"
        "a@x.com,b@x.com,Hello,Hi there,c@x.com,report.pdf,2026-12-01,09:30:00\n"
    )
    rows = parse_sheet(_csv_bytes(csv_text), "sheet.csv")
    assert rows == [
        {
            "to_email": "a@x.com",
            "from_email": "b@x.com",
            "subject": "Hello",
            "content": "Hi there",
            "cc": "c@x.com",
            "attachment_filename": "report.pdf",
            "send_date": "2026-12-01",
            "send_time": "09:30:00",
        }
    ]


def test_parse_sheet_blank_optional_columns():
    csv_text = (
        "To,From,Subject,Email Content\n"
        "a@x.com,b@x.com,Hello,Hi there\n"
    )
    rows = parse_sheet(_csv_bytes(csv_text), "sheet.csv")
    row = rows[0]
    assert row["cc"] is None
    assert row["attachment_filename"] is None
    assert row["send_date"] is None
    assert row["send_time"] is None


def test_parse_sheet_missing_required_column_raises():
    csv_text = "From,Subject,Email Content\nb@x.com,Hello,Hi there\n"
    with pytest.raises(SheetParseError, match="To"):
        parse_sheet(_csv_bytes(csv_text), "sheet.csv")
