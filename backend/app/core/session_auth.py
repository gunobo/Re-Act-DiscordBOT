from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from fastapi import HTTPException, Request

from app.core.config import settings

COOKIE_NAME = "react_admin_session"

_serializer = URLSafeTimedSerializer(settings.cookie_secret, salt="admin-session")


def create_session_value(discord_id: str, username: str) -> str:
    return _serializer.dumps({"discord_id": discord_id, "username": username})


def read_session_value(value: str) -> dict | None:
    try:
        return _serializer.loads(value, max_age=settings.session_max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None


def get_current_admin(request: Request) -> dict | None:
    raw = request.cookies.get(COOKIE_NAME)
    if not raw:
        return None
    return read_session_value(raw)


def require_admin(request: Request) -> dict:
    admin = get_current_admin(request)
    if not admin:
        raise HTTPException(status_code=303, headers={"Location": "/auth/login"})
    return admin
