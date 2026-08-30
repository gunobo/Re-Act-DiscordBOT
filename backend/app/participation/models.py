from datetime import datetime

from sqlmodel import Field, SQLModel, UniqueConstraint


class Participation(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("competition_category_id", "discord_id", name="uq_participation_unique"),
    )

    id: int | None = Field(default=None, primary_key=True)
    competition_category_id: int = Field(foreign_key="competitioncategory.id", index=True)
    discord_id: str = Field(index=True)
    joined_at: datetime = Field(default_factory=datetime.utcnow)
