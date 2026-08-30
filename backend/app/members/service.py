from sqlmodel import Session, select

from app.members.models import AllowedMember, Member


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_allowed_member(session: Session, email: str) -> AllowedMember | None:
    return session.get(AllowedMember, normalize_email(email))


def list_allowed_members(session: Session) -> list[AllowedMember]:
    return list(session.exec(select(AllowedMember).order_by(AllowedMember.created_at.desc())))


def add_allowed_member(
    session: Session, email: str, student_id: str, name: str, added_by: str
) -> AllowedMember:
    row = AllowedMember(
        email=normalize_email(email), student_id=student_id.strip(), name=name.strip(), added_by=added_by
    )
    session.add(row)
    session.commit()
    return row


def delete_allowed_member(session: Session, email: str) -> None:
    row = session.get(AllowedMember, normalize_email(email))
    if row:
        session.delete(row)
        session.commit()


def list_members(session: Session) -> list[Member]:
    return list(session.exec(select(Member).order_by(Member.verified_at.desc())))


def get_member(session: Session, discord_id: str) -> Member | None:
    return session.get(Member, discord_id)


def upsert_member(session: Session, discord_id: str, email: str, student_id: str, name: str) -> Member:
    row = session.get(Member, discord_id)
    if row:
        row.email = normalize_email(email)
        row.student_id = student_id
        row.name = name
    else:
        row = Member(discord_id=discord_id, email=normalize_email(email), student_id=student_id, name=name)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def delete_member(session: Session, discord_id: str) -> None:
    row = session.get(Member, discord_id)
    if row:
        session.delete(row)
        session.commit()
