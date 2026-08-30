from datetime import datetime

from sqlmodel import Field, SQLModel

DEFAULT_TEMPLATE_TEXT = (
    "🏆 **{title}**\n"
    "{description}\n\n"
    "카테고리: {category_name}\n"
    "마감: {deadline}\n"
    "정원: {capacity}명 (선착순)\n\n"
    "아래 버튼을 눌러 참가 신청하세요!"
)


class CategoryTemplate(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    template_text: str = DEFAULT_TEMPLATE_TEXT
    created_at: datetime = Field(default_factory=datetime.utcnow)
