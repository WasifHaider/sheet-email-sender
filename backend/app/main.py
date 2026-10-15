import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import batches, jobs, upload
from .scheduler import scheduler_loop

app = FastAPI(title="Sheet Email Sender")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(batches.router)
app.include_router(jobs.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
async def start_scheduler():
    asyncio.create_task(scheduler_loop())
