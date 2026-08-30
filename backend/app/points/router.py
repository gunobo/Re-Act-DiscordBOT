from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session

from app.core.internal_auth import require_internal_key
from app.db.session import get_session
from app.members import service as members_service
from app.points import service as points_service

router = APIRouter(
    prefix="/internal/points", tags=["points"], dependencies=[Depends(require_internal_key)]
)


class MyPointsResponse(BaseModel):
    ok: bool
    reason: str | None = None
    name: str | None = None
    total_points: int | None = None


@router.get("/me", response_model=MyPointsResponse)
def my_points(discord_id: str = Query(...), session: Session = Depends(get_session)):
    member = members_service.get_member(session, discord_id)
    if not member:
        return MyPointsResponse(ok=False, reason="not_verified")
    total = points_service.get_total_points(session, discord_id)
    return MyPointsResponse(ok=True, name=member.name, total_points=total)


class LeaderboardEntry(BaseModel):
    name: str
    student_id: str
    total_points: int


class LeaderboardResponse(BaseModel):
    entries: list[LeaderboardEntry]


@router.get("/leaderboard", response_model=LeaderboardResponse)
def leaderboard(limit: int = Query(10, ge=1, le=25), session: Session = Depends(get_session)):
    entries = points_service.get_leaderboard(session, limit=limit)
    return LeaderboardResponse(entries=entries)
