from datetime import datetime

from sqlmodel import Field, SQLModel


class VerificationCode(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    discord_id: str = Field(index=True)
    email: str
    code_hash: str
    attempts: int = 0
    consumed: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime

    def is_valid(self) -> bool:
        return not self.consumed and datetime.utcnow() < self.expires_at
