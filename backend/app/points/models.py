from datetime import datetime

from sqlmodel import Field, SQLModel


class PointTransaction(SQLModel, table=True):
    """포인트 지급/차감 내역. 총점은 항상 이 원장(ledger)의 합으로 계산한다."""

    id: int | None = Field(default=None, primary_key=True)
    discord_id: str = Field(index=True)
    points: int
    reason: str
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
