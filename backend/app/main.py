import asyncio
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .routers import auth, batches, jobs, upload
from .scheduler import scheduler_loop

app = FastAPI(title="Sheet Email Sender")

app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SESSION_SECRET", "dev-secret"))

frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(batches.router)
app.include_router(jobs.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
async def start_scheduler():
    asyncio.create_task(scheduler_loop())
