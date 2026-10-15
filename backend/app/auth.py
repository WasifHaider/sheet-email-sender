import os
import time

import jwt
from fastapi import HTTPException, Request

SESSION_COOKIE_NAME = "ses_auth"
SESSION_MAX_AGE_SECONDS = 7 * 24 * 60 * 60


def create_session_token(user_id: str, email: str) -> str:
    secret = os.environ["SESSION_SECRET"]
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": int(time.time()) + SESSION_MAX_AGE_SECONDS,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_session_token(token: str) -> dict:
    secret = os.environ["SESSION_SECRET"]
    return jwt.decode(token, secret, algorithms=["HS256"])


def get_current_user(request: Request) -> dict:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_session_token(token)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return {"id": payload["user_id"], "email": payload["email"]}
