from datetime import datetime

from sqlmodel import Session, select

from app import discord_rest
from app.notices.models import Notice

EMBED_COLOR = 0x57F287


def list_notices(session: Session, published_only: bool = False) -> list[Notice]:
    stmt = select(Notice).order_by(Notice.created_at.desc())
    if published_only:
        stmt = stmt.where(Notice.published == True)  # noqa: E712
    return list(session.exec(stmt))


def get_notice(session: Session, notice_id: int) -> Notice | None:
    return session.get(Notice, notice_id)


def create_notice(session: Session, title: str, content: str, created_by: str) -> Notice:
    row = Notice(title=title.strip(), content=content, created_by=created_by)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def update_notice(session: Session, notice_id: int, title: str, content: str) -> None:
    row = session.get(Notice, notice_id)
    if row:
        row.title = title.strip()
        row.content = content
        session.add(row)
        session.commit()


async def delete_notice(session: Session, notice_id: int) -> None:
    row = session.get(Notice, notice_id)
    if not row:
        return
    if row.discord_channel_id and row.discord_message_id:
        await discord_rest.delete_message(row.discord_channel_id, row.discord_message_id)
    session.delete(row)
    session.commit()


async def publish_notice(session: Session, notice_id: int, channel_id: str) -> Notice | None:
    row = session.get(Notice, notice_id)
    if not row:
        return None
    embed = {"title": row.title, "description": row.content, "color": EMBED_COLOR}
    message_id = await discord_rest.send_message(channel_id, embed=embed)
    row.published = True
    row.discord_channel_id = channel_id
    row.discord_message_id = message_id
    row.published_at = datetime.utcnow()
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
