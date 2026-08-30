from sqlmodel import Session, select

from app.categories.models import CategoryTemplate, CategoryTemplateChannel


def list_categories(session: Session) -> list[CategoryTemplate]:
    return list(session.exec(select(CategoryTemplate).order_by(CategoryTemplate.id)))


def get_category(session: Session, category_id: int) -> CategoryTemplate | None:
    return session.get(CategoryTemplate, category_id)


def create_category(session: Session, name: str) -> CategoryTemplate:
    row = CategoryTemplate(name=name.strip())
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def update_category(session: Session, category_id: int, name: str) -> None:
    row = session.get(CategoryTemplate, category_id)
    if row:
        row.name = name.strip()
        session.add(row)
        session.commit()


def delete_category(session: Session, category_id: int) -> None:
    row = session.get(CategoryTemplate, category_id)
    if not row:
        return
    for channel in list_channels_for_template(session, category_id):
        session.delete(channel)
    session.delete(row)
    session.commit()


def list_channels_for_template(session: Session, category_template_id: int) -> list[CategoryTemplateChannel]:
    return list(
        session.exec(
            select(CategoryTemplateChannel)
            .where(CategoryTemplateChannel.category_template_id == category_template_id)
            .order_by(CategoryTemplateChannel.sort_order, CategoryTemplateChannel.id)
        )
    )


def get_join_channel(session: Session, category_template_id: int) -> CategoryTemplateChannel | None:
    return session.exec(
        select(CategoryTemplateChannel).where(
            CategoryTemplateChannel.category_template_id == category_template_id,
            CategoryTemplateChannel.is_join_channel == True,  # noqa: E712
        )
    ).first()


def _unset_other_join_channels(session: Session, category_template_id: int, keep_id: int | None) -> None:
    for channel in list_channels_for_template(session, category_template_id):
        if channel.is_join_channel and channel.id != keep_id:
            channel.is_join_channel = False
            session.add(channel)


def add_channel(
    session: Session,
    category_template_id: int,
    name: str,
    template_text: str,
    is_join_channel: bool,
    is_public: bool = False,
    channel_type: int = 0,
) -> CategoryTemplateChannel:
    row = CategoryTemplateChannel(
        category_template_id=category_template_id,
        name=name.strip(),
        template_text=template_text,
        is_join_channel=is_join_channel,
        is_public=is_public,
        channel_type=channel_type,
    )
    if is_join_channel:
        _unset_other_join_channels(session, category_template_id, keep_id=None)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def update_channel(
    session: Session,
    channel_id: int,
    name: str,
    template_text: str,
    is_join_channel: bool,
    is_public: bool = False,
    channel_type: int = 0,
) -> None:
    row = session.get(CategoryTemplateChannel, channel_id)
    if not row:
        return
    row.name = name.strip()
    row.template_text = template_text
    row.is_join_channel = is_join_channel
    row.is_public = is_public
    row.channel_type = channel_type
    if is_join_channel:
        _unset_other_join_channels(session, row.category_template_id, keep_id=row.id)
    session.add(row)
    session.commit()


def delete_channel(session: Session, channel_id: int) -> None:
    row = session.get(CategoryTemplateChannel, channel_id)
    if row:
        session.delete(row)
        session.commit()
