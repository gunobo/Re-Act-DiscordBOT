from collections import defaultdict
from datetime import datetime

from sqlmodel import Session, select

from app import discord_rest
from app.categories import service as categories_service
from app.competitions.models import Competition, CompetitionCategory, CompetitionCategoryChannel
from app.core.config import settings
from app.participation.models import Participation

EMBED_COLOR = 0x5865F2


def render_template(template_text: str, **kwargs) -> str:
    safe = defaultdict(str, **kwargs)
    return template_text.format_map(safe)


def build_embed(
    competition: Competition, comp_category: CompetitionCategory, template_text: str, participant_count: int
) -> dict:
    rendered = render_template(
        template_text,
        title=competition.title,
        description=competition.description,
        category_name=comp_category.name,
        deadline=competition.deadline.strftime("%Y-%m-%d %H:%M"),
        capacity=comp_category.capacity,
    )
    return {
        "title": f"{competition.title} - {comp_category.name}",
        "description": rendered,
        "color": EMBED_COLOR,
        "fields": [
            {
                "name": "참가 현황",
                "value": f"{participant_count}/{comp_category.capacity}명",
                "inline": True,
            },
            {"name": "마감", "value": competition.deadline.strftime("%Y-%m-%d %H:%M"), "inline": True},
        ],
    }


def build_components(comp_category_id: int, disabled: bool) -> list:
    return [
        {
            "type": 1,
            "components": [
                {
                    "type": 2,
                    "style": 1,
                    "label": "참가하기",
                    "custom_id": f"join:{comp_category_id}",
                    "disabled": disabled,
                }
            ],
        }
    ]


def list_competitions(session: Session) -> list[Competition]:
    return list(session.exec(select(Competition).order_by(Competition.created_at.desc())))


def get_competition(session: Session, competition_id: int) -> Competition | None:
    return session.get(Competition, competition_id)


def list_categories_for_competition(session: Session, competition_id: int) -> list[CompetitionCategory]:
    return list(
        session.exec(
            select(CompetitionCategory).where(CompetitionCategory.competition_id == competition_id)
        )
    )


def list_channels_for_category(session: Session, competition_category_id: int) -> list[CompetitionCategoryChannel]:
    return list(
        session.exec(
            select(CompetitionCategoryChannel).where(
                CompetitionCategoryChannel.competition_category_id == competition_category_id
            )
        )
    )


def get_join_channel(session: Session, competition_category_id: int) -> CompetitionCategoryChannel | None:
    return session.exec(
        select(CompetitionCategoryChannel).where(
            CompetitionCategoryChannel.competition_category_id == competition_category_id,
            CompetitionCategoryChannel.is_join_channel == True,  # noqa: E712
        )
    ).first()


async def create_competition(
    session: Session,
    title: str,
    description: str,
    deadline: datetime,
    selections: list[dict],
    created_by: str,
) -> Competition:
    """selections: [{"category_template_id": int|None, "name": str, "capacity": int}, ...]"""
    competition = Competition(title=title, description=description, deadline=deadline, created_by=created_by)
    session.add(competition)
    session.commit()
    session.refresh(competition)

    # 대회 참가자에게 부여할 "대회명" 역할을 미리 만들어둔다.
    role_id = await discord_rest.create_role(settings.discord_guild_id, title)
    competition.discord_role_id = role_id

    # 대회 전용 디스코드 카테고리(채널 묶음)를 만들고, 이 대회의 모든 채널을 그 안에 생성한다.
    category_channel_id = await discord_rest.create_channel(
        settings.discord_guild_id, title, parent_id=None, channel_type=4
    )
    competition.discord_category_channel_id = category_channel_id

    session.add(competition)
    session.commit()

    for selection in selections:
        comp_category = CompetitionCategory(
            competition_id=competition.id,
            category_template_id=selection.get("category_template_id"),
            name=selection["name"],
            capacity=selection["capacity"],
        )
        session.add(comp_category)
        session.commit()
        session.refresh(comp_category)

        channel_defs = (
            categories_service.list_channels_for_template(session, selection["category_template_id"])
            if selection.get("category_template_id")
            else []
        )

        for channel_def in channel_defs:
            channel_name = f"{comp_category.name}-{channel_def.name}"
            channel_id = await discord_rest.create_channel(
                settings.discord_guild_id, channel_name, parent_id=category_channel_id
            )

            message_id = None
            if channel_def.is_join_channel:
                embed = build_embed(competition, comp_category, channel_def.template_text, participant_count=0)
                components = build_components(comp_category.id, disabled=False)
                message_id = await discord_rest.send_message(channel_id, embed=embed, components=components)
            elif channel_def.template_text.strip():
                rendered = render_template(
                    channel_def.template_text,
                    title=competition.title,
                    description=competition.description,
                    category_name=comp_category.name,
                    deadline=deadline.strftime("%Y-%m-%d %H:%M"),
                    capacity=comp_category.capacity,
                )
                message_id = await discord_rest.send_message(channel_id, content=rendered)

            session.add(
                CompetitionCategoryChannel(
                    competition_category_id=comp_category.id,
                    name=channel_def.name,
                    template_text=channel_def.template_text,
                    is_join_channel=channel_def.is_join_channel,
                    discord_channel_id=channel_id,
                    discord_message_id=message_id,
                )
            )
            session.commit()

    return competition


async def delete_competition(session: Session, competition_id: int) -> None:
    """대회와 그 카테고리 채널/역할을 디스코드에서도 함께 정리하고 DB 기록을 삭제한다."""
    competition = session.get(Competition, competition_id)
    if not competition:
        return

    comp_categories = list_categories_for_competition(session, competition_id)
    for comp_category in comp_categories:
        for channel in list_channels_for_category(session, comp_category.id):
            await discord_rest.delete_channel(channel.discord_channel_id)
            session.delete(channel)
        for participation in session.exec(
            select(Participation).where(Participation.competition_category_id == comp_category.id)
        ):
            session.delete(participation)
        session.delete(comp_category)

    if competition.discord_category_channel_id:
        await discord_rest.delete_channel(competition.discord_category_channel_id)
    if competition.discord_role_id:
        await discord_rest.delete_role(settings.discord_guild_id, competition.discord_role_id)

    session.delete(competition)
    session.commit()
