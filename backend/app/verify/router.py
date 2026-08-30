import hashlib
import random
from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlmodel import Session, select

from app import discord_rest
from app.core.config import settings
from app.core.internal_auth import require_internal_key
from app.db.session import get_session
from app.members import service as members_service
from app.settings_kv import service as settings_service
from app.verify.mailer import send_verification_email
from app.verify.models import VerificationCode

router = APIRouter(
    prefix="/internal/verify", tags=["verify"], dependencies=[Depends(require_internal_key)]
)


def _hash_code(discord_id: str, code: str) -> str:
    raw = f"{discord_id}:{code}:{settings.cookie_secret}"
    return hashlib.sha256(raw.encode()).hexdigest()


class StartRequest(BaseModel):
    discord_id: str
    email: str


class StartResponse(BaseModel):
    ok: bool
    reason: str | None = None


@router.post("/start", response_model=StartResponse)
def start_verification(
    body: StartRequest, background_tasks: BackgroundTasks, session: Session = Depends(get_session)
):
    email = members_service.normalize_email(body.email)
    allowed = members_service.get_allowed_member(session, email)
    if not allowed:
        return StartResponse(ok=False, reason="not_whitelisted")

    if members_service.get_member(session, body.discord_id):
        return StartResponse(ok=False, reason="already_verified")

    # 기존에 발급된 미사용 코드는 무효화
    for pending in session.exec(
        select(VerificationCode).where(
            VerificationCode.discord_id == body.discord_id, VerificationCode.consumed == False  # noqa: E712
        )
    ):
        pending.consumed = True
        session.add(pending)

    code = f"{random.randint(0, 999999):06d}"
    row = VerificationCode(
        discord_id=body.discord_id,
        email=email,
        code_hash=_hash_code(body.discord_id, code),
        expires_at=datetime.utcnow() + timedelta(minutes=settings.verification_code_ttl_minutes),
    )
    session.add(row)
    session.commit()

    background_tasks.add_task(send_verification_email, email, code, allowed.name)
    return StartResponse(ok=True)


class ConfirmRequest(BaseModel):
    discord_id: str
    code: str


class ConfirmResponse(BaseModel):
    ok: bool
    reason: str | None = None
    name: str | None = None
    student_id: str | None = None
    nickname: str | None = None
    granted_role_names: list[str] = []


@router.post("/confirm", response_model=ConfirmResponse)
async def confirm_verification(body: ConfirmRequest, session: Session = Depends(get_session)):
    pending = session.exec(
        select(VerificationCode)
        .where(VerificationCode.discord_id == body.discord_id, VerificationCode.consumed == False)  # noqa: E712
        .order_by(VerificationCode.created_at.desc())
    ).first()

    if not pending or not pending.is_valid():
        return ConfirmResponse(ok=False, reason="no_pending")

    if pending.attempts >= settings.verification_max_attempts:
        return ConfirmResponse(ok=False, reason="too_many_attempts")

    if pending.code_hash != _hash_code(body.discord_id, body.code.strip()):
        pending.attempts += 1
        session.add(pending)
        session.commit()
        return ConfirmResponse(ok=False, reason="invalid_code")

    pending.consumed = True
    session.add(pending)
    session.commit()

    allowed = members_service.get_allowed_member(session, pending.email)
    if not allowed:
        return ConfirmResponse(ok=False, reason="not_whitelisted")

    member = members_service.upsert_member(
        session, body.discord_id, allowed.email, allowed.student_id, allowed.name
    )

    guild_id = settings.discord_guild_id
    role_ids = settings_service.get_verified_role_ids(session)
    granted_role_names: list[str] = []
    if role_ids:
        roles = {r["id"]: r["name"] for r in await discord_rest.list_roles(guild_id)}
        for role_id in role_ids:
            await discord_rest.grant_role(guild_id, body.discord_id, role_id)
            granted_role_names.append(roles.get(role_id, role_id))

    nickname_format = settings_service.get_nickname_format(session)
    nickname = nickname_format.format(student_id=member.student_id, name=member.name, email=member.email)
    await discord_rest.set_nickname(guild_id, body.discord_id, nickname)

    return ConfirmResponse(
        ok=True,
        name=member.name,
        student_id=member.student_id,
        nickname=nickname,
        granted_role_names=granted_role_names,
    )
