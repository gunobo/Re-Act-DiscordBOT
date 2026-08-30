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
    """대회 등록 시 선택하는 카테고리(예: 웹개발). 실제 디스코드 채널은
    CategoryTemplateChannel에 정의해둔 만큼 그 안에 여러 개 생성된다."""

    id: int | None = Field(default=None, primary_key=True)
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CategoryTemplateChannel(SQLModel, table=True):
    """카테고리 템플릿에 속한 채널 하나. is_join_channel=True인 채널에만
    참가 인원/정원 임베드와 '참가하기' 버튼이 올라간다 (템플릿당 최대 1개)."""

    id: int | None = Field(default=None, primary_key=True)
    category_template_id: int = Field(foreign_key="categorytemplate.id", index=True)
    name: str
    template_text: str = ""
    is_join_channel: bool = False
    sort_order: int = 0
