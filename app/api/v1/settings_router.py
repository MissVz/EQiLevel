from fastapi import APIRouter, Depends, Body
from app.services.security import require_admin
from app.services import storage

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

@router.get("/system_prompt")
def get_system_prompt(_=Depends(require_admin)):
    return {"system_prompt": storage.get_system_prompt()}

@router.post("/system_prompt")
def set_system_prompt(value: str = Body("", embed=True), _=Depends(require_admin)):
    # If empty, delete to fall back to default
    storage.set_setting("system_prompt", value.strip())
    return {"ok": True}

