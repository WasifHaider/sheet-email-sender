import pathlib
from email.message import EmailMessage

from app.mailer import build_message, get_access_token, send_via_gmail_api


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


class _FakeResponse:
    def __init__(self, json_data):
        self._json_data = json_data

    def raise_for_status(self):
        pass

    def json(self):
        return self._json_data


def test_get_access_token_calls_google_token_endpoint(monkeypatch):
    captured = {}

    def fake_post(url, data=None, timeout=None, **kwargs):
        captured["url"] = url
        captured["data"] = data
        return _FakeResponse({"access_token": "new-access-token"})

    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr("app.mailer.httpx.post", fake_post)

    token = get_access_token("refresh-abc")

    assert token == "new-access-token"
    assert captured["url"] == "https://oauth2.googleapis.com/token"
    assert captured["data"]["refresh_token"] == "refresh-abc"
    assert captured["data"]["grant_type"] == "refresh_token"


def test_send_via_gmail_api_posts_base64_message(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None, **kwargs):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return _FakeResponse({"id": "msg-1"})

    monkeypatch.setattr("app.mailer.httpx.post", fake_post)

    msg = EmailMessage()
    msg["To"] = "a@x.com"
    msg["From"] = "b@x.com"
    msg["Subject"] = "Hi"
    msg.set_content("Body")

    send_via_gmail_api("access-token-123", msg)

    assert captured["url"] == "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
    assert captured["headers"]["Authorization"] == "Bearer access-token-123"
    assert "raw" in captured["json"]
