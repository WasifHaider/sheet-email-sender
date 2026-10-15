import os

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from ..auth import SESSION_MAX_AGE_SECONDS, SESSION_COOKIE_NAME, create_session_token, get_current_user
from ..db import get_supabase

router = APIRouter()

oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile https://www.googleapis.com/auth/gmail.send",
        "prompt": "consent",
        "access_type": "offline",
    },
)


@router.get("/auth/google/login")
async def google_login(request: Request):
    redirect_uri = os.environ["GOOGLE_REDIRECT_URI"]
    return await oauth.google.authorize_redirect(
        request, redirect_uri, access_type="offline", prompt="consent"
    )


@router.get("/auth/google/callback")
async def google_callback(request: Request, db=Depends(get_supabase)):
    token = await oauth.google.authorize_access_token(request)
    userinfo = token["userinfo"]
    sub = userinfo["sub"]
    email = userinfo["email"]
    name = userinfo.get("name")
    refresh_token = token.get("refresh_token")

    existing = db.table("users").select("*").eq("google_sub", sub).execute().data
    if existing:
        user_id = existing[0]["id"]
        update_fields = {"email": email, "name": name}
        if refresh_token:
            update_fields["refresh_token"] = refresh_token
        db.table("users").update(update_fields).eq("id", user_id).execute()
    else:
        if not refresh_token:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Google didn't grant offline access, so we can't send email as you yet. "
                    "Revoke this app's access at https://myaccount.google.com/permissions and try signing in again."
                ),
            )
        inserted = db.table("users").insert(
            [{"google_sub": sub, "email": email, "name": name, "refresh_token": refresh_token}]
        ).execute().data
        user_id = inserted[0]["id"]

    session_token = create_session_token(user_id, email)
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    response = RedirectResponse(url=f"{frontend_url}/upload")
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        samesite="lax",
        max_age=SESSION_MAX_AGE_SECONDS,
    )
    return response


@router.get("/auth/me")
def me(user: dict = Depends(get_current_user)):
    return user


@router.post("/auth/logout")
def logout():
    response = JSONResponse({"status": "logged_out"})
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response
