import base64
import os
import pathlib
from email.message import EmailMessage
from typing import Optional

import httpx

TOKEN_URL = "https://oauth2.googleapis.com/token"
SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


def build_message(job: dict, attachment_path: Optional[pathlib.Path]) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = job["subject"]
    msg["From"] = job["from_email"]
    msg["To"] = job["to_email"]
    if job.get("cc"):
        msg["Cc"] = job["cc"]
    msg.set_content(job["content"])

    if attachment_path and attachment_path.exists():
        data = attachment_path.read_bytes()
        msg.add_attachment(
            data,
            maintype="application",
            subtype="octet-stream",
            filename=attachment_path.name,
        )
    return msg


def get_access_token(refresh_token: str) -> str:
    response = httpx.post(
        TOKEN_URL,
        data={
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def send_via_gmail_api(access_token: str, msg: EmailMessage) -> None:
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    response = httpx.post(
        SEND_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        json={"raw": raw},
        timeout=15,
    )
    response.raise_for_status()
