import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, func, select

from app import discord_rest
from app.competitions import service as competitions_service
from app.competitions.models import Competition, CompetitionCategory
from app.core.config import settings
from app.core.internal_auth import require_internal_key
from app.db.session import get_session
from app.members import service as members_service
from app.participation.models import Participation
from app.points import service as points_service
from app.settings_kv import service as settings_service

router = APIRouter(
    prefix="/internal/participation", tags=["participation"], dependencies=[Depends(require_internal_key)]
)

_locks: dict[int, asyncio.Lock] = {}
_locks_guard = asyncio.Lock()


async def _lock_for(comp_category_id: int) -> asyncio.Lock:
    async with _locks_guard:
        if comp_category_id not in _locks:
            _locks[comp_category_id] = asyncio.Lock()
        return _locks[comp_category_id]


def _count_participants(session: Session, comp_category_id: int) -> int:
    return session.exec(
        select(func.count()).select_from(Participation).where(
            Participation.competition_category_id == comp_category_id
        )
    ).one()


class JoinRequest(BaseModel):
    competition_category_id: int
    discord_id: str


class JoinResponse(BaseModel):
    ok: bool
    message: str


@router.post("/join", response_model=JoinResponse)
async def join_competition(body: JoinRequest, session: Session = Depends(get_session)):
    if not members_service.get_member(session, body.discord_id):
        return JoinResponse(ok=False, message="부원 인증 후 참가할 수 있습니다. `/인증`을 먼저 진행해주세요.")

    comp_category = session.get(CompetitionCategory, body.competition_category_id)
    if not comp_category:
        return JoinResponse(ok=False, message="존재하지 않는 참가 항목입니다.")

    competition = session.get(Competition, comp_category.competition_id)
    if not competition:
        return JoinResponse(ok=False, message="존재하지 않는 대회입니다.")

    if datetime.utcnow() > competition.deadline:
        return JoinResponse(ok=False, message="마감된 대회입니다.")

    lock = await _lock_for(comp_category.id)
    async with lock:
        already = session.exec(
            select(Participation).where(
                Participation.competition_category_id == comp_category.id,
                Participation.discord_id == body.discord_id,
            )
        ).first()
        if already:
            return JoinResponse(ok=False, message="이미 참가 신청하셨습니다.")

        current_count = _count_participants(session, comp_category.id)
        if current_count >= comp_category.capacity:
            return JoinResponse(ok=False, message="정원이 마감되었습니다.")

        session.add(Participation(competition_category_id=comp_category.id, discord_id=body.discord_id))
        session.commit()

        if competition.discord_role_id:
            await discord_rest.grant_role(
                settings.discord_guild_id, body.discord_id, competition.discord_role_id
            )

        points = settings_service.get_points_per_join(session)
        if points:
            points_service.add_points(
                session,
                body.discord_id,
                points,
                reason=f"참가: {competition.title} - {comp_category.name}",
                created_by="system",
            )

        new_count = current_count + 1
        is_full = new_count >= comp_category.capacity

        if comp_category.discord_channel_id and comp_category.discord_message_id:
            embed = competitions_service.build_embed(competition, comp_category, new_count)
            components = competitions_service.build_components(comp_category.id, disabled=is_full)
            await discord_rest.edit_message(
                comp_category.discord_channel_id, comp_category.discord_message_id, embed, components
            )

        dm_text = f"'{competition.title} - {comp_category.name}' 대회에 참가 완료되었습니다!"
        if points:
            dm_text += f" (+{points}P)"
        await discord_rest.send_dm(body.discord_id, dm_text)

        return JoinResponse(ok=True, message=dm_text)
