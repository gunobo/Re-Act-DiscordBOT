from datetime import datetime

from sqlmodel import Field, SQLModel, UniqueConstraint


class AttributeDefinition(SQLModel, table=True):
    """관리자가 자유롭게 정의하는 부원 속성 항목 (예: 전공, 연락처, 티셔츠 사이즈).

    디스코드 역할/닉네임에는 반영되지 않고, 관리 웹의 내부 기록/CSV 내보내기용으로만 쓰인다.
    """

    id: int | None = Field(default=None, primary_key=True)
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AttributeValue(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("discord_id", "definition_id", name="uq_attribute_value_unique"),)

    id: int | None = Field(default=None, primary_key=True)
    discord_id: str = Field(index=True)
    definition_id: int = Field(foreign_key="attributedefinition.id", index=True)
    value: str
