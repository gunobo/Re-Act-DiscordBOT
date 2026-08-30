import urllib.parse

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session

from app import discord_rest
from app.core.config import settings
from app.core.session_auth import COOKIE_NAME, create_session_value
from app.db.session import get_session
from app.settings_kv import service as settings_service

router = APIRouter(prefix="/auth", tags=["auth"])

DISCORD_OAUTH_AUTHORIZE = "https://discord.com/oauth2/authorize"
DISCORD_OAUTH_TOKEN = "https://discord.com/api/oauth2/token"
DISCORD_API_ME = "https://discord.com/api/v10/users/@me"


def _redirect_uri() -> str:
    return f"{settings.web_base_url}/auth/discord/callback"


@router.get("/login")
def login_page():
    return RedirectResponse(url="/auth/discord/login")


@router.get("/discord/login")
def discord_login():
    params = {
        "client_id": settings.discord_client_id,
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": "identify",
    }
    url = f"{DISCORD_OAUTH_AUTHORIZE}?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url=url)


@router.get("/discord/callback")
async def discord_callback(code: str, session: Session = Depends(get_session)):
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            DISCORD_OAUTH_TOKEN,
            data={
                "client_id": settings.discord_client_id,
                "client_secret": settings.discord_client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": _redirect_uri(),
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]

        me_resp = await client.get(
            DISCORD_API_ME, headers={"Authorization": f"Bearer {access_token}"}
        )
        me_resp.raise_for_status()
        me = me_resp.json()

    discord_id = me["id"]
    username = me.get("username", discord_id)

    is_admin = discord_id in settings.super_admin_ids
    if not is_admin:
        admin_role_id = settings_service.get_admin_role_id(session)
        if admin_role_id:
            role_ids = await discord_rest.get_member_role_ids(settings.discord_guild_id, discord_id)
            is_admin = admin_role_id in role_ids

    if not is_admin:
        return RedirectResponse(url="/auth/forbidden")

    response = RedirectResponse(url="/admin")
    response.set_cookie(
        COOKIE_NAME,
        create_session_value(discord_id, username),
        max_age=settings.session_max_age_seconds,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/forbidden")
def forbidden():
    return HTMLResponse(
        "<h1>권한이 없습니다</h1><p>운영진 역할이 없는 계정입니다. 관리자에게 문의하세요.</p>",
        status_code=403,
    )


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie(COOKIE_NAME)
    return response
