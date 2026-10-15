import os
import pathlib
import smtplib
from email.message import EmailMessage
from typing import Optional


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


def send_message(msg: EmailMessage) -> None:
    host = os.environ["SMTP_HOST"]
    port = int(os.environ["SMTP_PORT"])
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)
