from collections import defaultdict
from datetime import datetime

from sqlmodel import Session, select

from app import discord_rest
from app.categories.models import DEFAULT_TEMPLATE_TEXT, CategoryTemplate
from app.competitions.models import Competition, CompetitionCategory
from app.core.config import settings
from app.settings_kv import service as settings_service

EMBED_COLOR = 0x5865F2


def render_template(template_text: str, **kwargs) -> str:
    safe = defaultdict(str, **kwargs)
    return template_text.format_map(safe)


def build_embed(competition: Competition, comp_category: CompetitionCategory, participant_count: int) -> dict:
    rendered = render_template(
        comp_category.template_text,
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
    session.add(competition)
    session.commit()

    parent_channel_id = settings_service.get_competition_parent_channel_id(session)

    for selection in selections:
        template_text = DEFAULT_TEMPLATE_TEXT
        if selection.get("category_template_id"):
            template = session.get(CategoryTemplate, selection["category_template_id"])
            if template:
                template_text = template.template_text

        comp_category = CompetitionCategory(
            competition_id=competition.id,
            category_template_id=selection.get("category_template_id"),
            name=selection["name"],
            template_text=template_text,
            capacity=selection["capacity"],
        )
        session.add(comp_category)
        session.commit()
        session.refresh(comp_category)

        channel_name = f"{title}-{comp_category.name}"
        channel_id = await discord_rest.create_channel(
            settings.discord_guild_id, channel_name, parent_id=parent_channel_id
        )
        comp_category.discord_channel_id = channel_id

        embed = build_embed(competition, comp_category, participant_count=0)
        components = build_components(comp_category.id, disabled=False)
        message_id = await discord_rest.send_message(channel_id, embed=embed, components=components)
        comp_category.discord_message_id = message_id

        session.add(comp_category)
        session.commit()

    return competition
