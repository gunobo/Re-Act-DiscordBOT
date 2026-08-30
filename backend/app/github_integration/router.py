import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlmodel import Session

from app import discord_rest
from app.core.config import settings
from app.db.session import get_session
from app.github_integration import service as github_service
from app.settings_kv import service as settings_service

router = APIRouter(prefix="/webhooks/github", tags=["github"])


@router.post("")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
    session: Session = Depends(get_session),
):
    body = await request.body()

    if not github_service.verify_signature(settings.github_webhook_secret, body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="invalid signature")

    if x_github_event == "ping":
        return {"ok": True}

    payload = json.loads(body or b"{}")
    embed = github_service.build_embed(x_github_event or "", payload)
    if not embed:
        return {"ok": True, "ignored": True}

    channel_id = settings_service.get_github_channel_id(session)
    if channel_id:
        await discord_rest.send_message(channel_id, embed=embed)

    return {"ok": True}
