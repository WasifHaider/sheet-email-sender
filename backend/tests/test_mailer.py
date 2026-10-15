import pathlib
from email.message import EmailMessage

import pytest

from app.mailer import build_message, send_message


def test_build_message_sets_headers_and_body():
    job = {
        "to_email": "a@x.com",
        "from_email": "b@x.com",
        "cc": "c@x.com",
        "subject": "Hello",
        "content": "Hi there",
    }
    msg = build_message(job, attachment_path=None)

    assert msg["To"] == "a@x.com"
    assert msg["From"] == "b@x.com"
    assert msg["Cc"] == "c@x.com"
    assert msg["Subject"] == "Hello"
    assert msg.get_content().strip() == "Hi there"


def test_build_message_attaches_file(tmp_path):
    attachment = tmp_path / "report.txt"
    attachment.write_text("data")
    job = {"to_email": "a@x.com", "from_email": "b@x.com", "cc": None,
           "subject": "Hello", "content": "Hi there"}

    msg = build_message(job, attachment_path=attachment)

    attachments = list(msg.iter_attachments())
    assert len(attachments) == 1
    assert attachments[0].get_filename() == "report.txt"


def test_send_message_calls_smtp(monkeypatch):
    sent = {}

    class FakeSMTP:
        def __init__(self, host, port):
            sent["host"] = host
            sent["port"] = port

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self):
            sent["starttls"] = True

        def login(self, user, password):
            sent["login"] = (user, password)

        def send_message(self, msg):
            sent["message"] = msg

    monkeypatch.setenv("SMTP_HOST", "smtp.test.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "user@test.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.setattr("app.mailer.smtplib.SMTP", FakeSMTP)

    msg = EmailMessage()
    msg["To"] = "a@x.com"
    send_message(msg)

    assert sent["host"] == "smtp.test.com"
    assert sent["port"] == 587
    assert sent["login"] == ("user@test.com", "secret")
    assert sent["message"] is msg
