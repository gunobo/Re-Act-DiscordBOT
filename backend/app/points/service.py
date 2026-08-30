from sqlmodel import Session, func, select

from app.members.models import Member
from app.points.models import PointTransaction


def add_points(session: Session, discord_id: str, points: int, reason: str, created_by: str) -> None:
    session.add(
        PointTransaction(discord_id=discord_id, points=points, reason=reason, created_by=created_by)
    )
    session.commit()


def get_total_points(session: Session, discord_id: str) -> int:
    total = session.exec(
        select(func.coalesce(func.sum(PointTransaction.points), 0)).where(
            PointTransaction.discord_id == discord_id
        )
    ).one()
    return int(total)


def get_leaderboard(session: Session, limit: int = 10) -> list[dict]:
    rows = session.exec(
        select(
            Member.discord_id,
            Member.name,
            Member.student_id,
            func.coalesce(func.sum(PointTransaction.points), 0).label("total_points"),
        )
        .join(PointTransaction, PointTransaction.discord_id == Member.discord_id, isouter=True)
        .group_by(Member.discord_id)
        .order_by(func.coalesce(func.sum(PointTransaction.points), 0).desc())
        .limit(limit)
    ).all()
    return [
        {"discord_id": r[0], "name": r[1], "student_id": r[2], "total_points": int(r[3])} for r in rows
    ]


def list_all_with_totals(session: Session) -> list[dict]:
    return get_leaderboard(session, limit=10_000)


def list_recent_transactions(session: Session, discord_id: str, limit: int = 20) -> list[PointTransaction]:
    return list(
        session.exec(
            select(PointTransaction)
            .where(PointTransaction.discord_id == discord_id)
            .order_by(PointTransaction.created_at.desc())
            .limit(limit)
        )
    )


def list_recent_transactions_all(session: Session, limit: int = 50) -> list[dict]:
    rows = session.exec(
        select(PointTransaction, Member)
        .join(Member, Member.discord_id == PointTransaction.discord_id, isouter=True)
        .order_by(PointTransaction.created_at.desc())
        .limit(limit)
    ).all()
    return [
        {
            "id": tx.id,
            "discord_id": tx.discord_id,
            "name": member.name if member else tx.discord_id,
            "points": tx.points,
            "reason": tx.reason,
            "created_at": tx.created_at,
        }
        for tx, member in rows
    ]


def delete_transaction(session: Session, transaction_id: int) -> None:
    row = session.get(PointTransaction, transaction_id)
    if row:
        session.delete(row)
        session.commit()
