from datetime import datetime

from sqlmodel import Field, SQLModel


class Competition(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    description: str
    deadline: datetime
    created_by: str
    discord_role_id: str | None = None
    discord_category_channel_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CompetitionCategory(SQLModel, table=True):
    """대회에 선택된 카테고리 하나. 실제 디스코드 채널들은
    CompetitionCategoryChannel에 (카테고리 템플릿의 채널 정의 개수만큼) 생성된다."""

    id: int | None = Field(default=None, primary_key=True)
    competition_id: int = Field(foreign_key="competition.id", index=True)
    category_template_id: int | None = Field(default=None, foreign_key="categorytemplate.id")
    name: str
    capacity: int


class CompetitionCategoryChannel(SQLModel, table=True):
    """실제로 생성된 채널 하나. is_join_channel=True인 채널에만 참가 인원/버튼이 붙는다."""

    id: int | None = Field(default=None, primary_key=True)
    competition_category_id: int = Field(foreign_key="competitioncategory.id", index=True)
    name: str
    template_text: str = ""
    is_join_channel: bool = False
    discord_channel_id: str
    discord_message_id: str | None = None
