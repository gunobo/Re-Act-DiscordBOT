from datetime import datetime

from sqlmodel import Field, SQLModel


class AllowedMember(SQLModel, table=True):
    """관리자가 웹에서 등록한, 인증을 시도할 수 있는 학교 이메일 화이트리스트."""

    email: str = Field(primary_key=True)
    student_id: str
    name: str
    added_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Member(SQLModel, table=True):
    """실제로 인증을 완료한 부원."""

    discord_id: str = Field(primary_key=True)
    email: str
    student_id: str
    name: str
    verified_at: datetime = Field(default_factory=datetime.utcnow)
