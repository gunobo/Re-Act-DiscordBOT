from sqlmodel import Session, select

from app.member_attributes.models import AttributeDefinition, AttributeValue


def list_definitions(session: Session) -> list[AttributeDefinition]:
    return list(session.exec(select(AttributeDefinition).order_by(AttributeDefinition.id)))


def get_definition(session: Session, definition_id: int) -> AttributeDefinition | None:
    return session.get(AttributeDefinition, definition_id)


def create_definition(session: Session, name: str) -> AttributeDefinition:
    row = AttributeDefinition(name=name.strip())
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def delete_definition(session: Session, definition_id: int) -> None:
    row = session.get(AttributeDefinition, definition_id)
    if not row:
        return
    for value in session.exec(
        select(AttributeValue).where(AttributeValue.definition_id == definition_id)
    ):
        session.delete(value)
    session.delete(row)
    session.commit()


def get_values_for_member(session: Session, discord_id: str) -> dict[int, str]:
    rows = session.exec(select(AttributeValue).where(AttributeValue.discord_id == discord_id))
    return {row.definition_id: row.value for row in rows}


def set_value(session: Session, discord_id: str, definition_id: int, value: str) -> None:
    existing = session.exec(
        select(AttributeValue).where(
            AttributeValue.discord_id == discord_id, AttributeValue.definition_id == definition_id
        )
    ).first()
    value = value.strip()
    if existing:
        if not value:
            session.delete(existing)
        else:
            existing.value = value
            session.add(existing)
    elif value:
        session.add(AttributeValue(discord_id=discord_id, definition_id=definition_id, value=value))
    session.commit()


def get_values_map(session: Session, definition_ids: list[int]) -> dict[tuple[str, int], str]:
    if not definition_ids:
        return {}
    rows = session.exec(
        select(AttributeValue).where(AttributeValue.definition_id.in_(definition_ids))
    )
    return {(row.discord_id, row.definition_id): row.value for row in rows}
