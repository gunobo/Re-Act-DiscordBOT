from fastapi import Header, HTTPException

from app.core.config import settings


def require_internal_key(x_internal_key: str = Header(default="")) -> None:
    if x_internal_key != settings.internal_api_key:
        raise HTTPException(status_code=401, detail="invalid internal key")
