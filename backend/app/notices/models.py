from datetime import datetime

from sqlmodel import Field, SQLModel


class Notice(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    content: str
    published: bool = False
    discord_channel_id: str | None = None
    discord_message_id: str | None = None
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    published_at: datetime | None = None
