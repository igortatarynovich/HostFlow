from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.scan import router as scan_router, SCAN_STORAGE_ROOT

MAX_CONTENT_SIZE = int(os.getenv("SCAN_MAX_CONTENT_SIZE", "52428800"))  # 50 MB default

app = FastAPI(title="HostFlow Scanner API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def limit_upload_size(request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_CONTENT_SIZE:
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse("Request too large", status_code=413)
    return await call_next(request)


app.include_router(scan_router)

# Serve stored files
SCAN_STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
app.mount(
    "/api/uploads/scanner",
    StaticFiles(directory=SCAN_STORAGE_ROOT, html=False),
    name="scanner-uploads",
)


@app.get("/health")
async def health():
    return {"status": "ok"}
