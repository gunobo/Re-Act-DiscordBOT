from datetime import datetime

from sqlmodel import Field, SQLModel


class Competition(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    description: str
    deadline: datetime
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CompetitionCategory(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    competition_id: int = Field(foreign_key="competition.id", index=True)
    category_template_id: int | None = Field(default=None, foreign_key="categorytemplate.id")
    name: str
    template_text: str
    capacity: int
    discord_channel_id: str | None = None
    discord_message_id: str | None = None
