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
    """카테고리 템플릿에 속한 채널 하나. is_join_channel=True인 채널(템플릿당 최대 1개)에만
    참가 인원/정원 임베드와 '참가하기' 버튼이 올라가고, 아직 역할이 없는 사람도 봐야 하니
    비공개 카테고리 밖(서버 최상위)에 만들어진다. 나머지 채널은 대회 역할을 가진 사람만
    보이는 비공개 카테고리 안에 생성된다.

    channel_type: 0 = 텍스트 채널, 2 = 음성 채널 (Discord 채널 타입 값)."""

    id: int | None = Field(default=None, primary_key=True)
    category_template_id: int = Field(foreign_key="categorytemplate.id", index=True)
    name: str
    template_text: str = ""
    is_join_channel: bool = False
    channel_type: int = 0
    sort_order: int = 0
