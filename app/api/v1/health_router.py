# app/api/v1/health_router.py
import os

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.services import storage  # expects storage.db_health() -> (ok: bool, err: Optional[str])
import shutil
from app.services.storage import db_health

router = APIRouter(prefix="/api/v1", tags=["health"])

@router.get("/health")
def health():
    import shutil as _sh
    return {"status": "ok", "ffmpeg": "present" if _sh.which("ffmpeg") else "missing"}

@router.get("/health/full")
def health_full():
    # OpenAI key check
    key_ok = bool(os.getenv("OPENAI_API_KEY"))

    # DB health
    db_ok, db_err = storage.db_health()

    # ffmpeg on PATH (for Whisper decoding of webm/opus)
    ffmpeg_ok = bool(shutil.which("ffmpeg"))

    overall_ok = key_ok and db_ok
    # Stream watchdog settings (from env)
    stream_cfg = {
        "max_seconds": float(os.getenv("STREAM_MAX_SECONDS", "25")),
        "stale_partial_seconds": float(os.getenv("STREAM_STALE_PARTIAL_SECONDS", "10")),
    }

    payload = {
        "status": "ok" if overall_ok else "degraded",
        "components": {
            "openai_key": "present" if key_ok else "missing",
            "database": "up" if db_ok else "down",
            "ffmpeg": "present" if ffmpeg_ok else "missing",
        },
        "stream": stream_cfg,
        "errors": {},
    }

    if not db_ok and db_err:
        payload["errors"]["database"] = db_err

    code = status.HTTP_200_OK if overall_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(content=payload, status_code=code)
