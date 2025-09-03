import os
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

_api_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)

def require_admin(api_key: str | None = Security(_api_key_header)):
    expected = os.getenv("ADMIN_API_KEY")
    if expected and api_key != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")
