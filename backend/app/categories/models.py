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
    """카테고리 템플릿에 속한 채널(또는 참가 신청 항목) 하나.

    is_join_channel=True인 행(템플릿당 최대 1개)은 새 채널을 만들지 않고, 관리자가
    설정(`/admin/settings`)에 미리 지정해둔 기존 "참가 신청 채널"에 정원/참가 버튼이
    달린 안내 메시지만 올린다.

    나머지 행은 실제로 채널을 새로 만든다: is_public=True면 서버 최상위에 공개로,
    False면 대회 전용 비공개 카테고리 안에(대회 역할을 가진 사람만 보이게) 생성된다.

    channel_type: 0 = 텍스트 채널, 2 = 음성 채널 (Discord 채널 타입 값)."""

    id: int | None = Field(default=None, primary_key=True)
    category_template_id: int = Field(foreign_key="categorytemplate.id", index=True)
    name: str
    template_text: str = ""
    is_join_channel: bool = False
    is_public: bool = False
    channel_type: int = 0
    sort_order: int = 0
