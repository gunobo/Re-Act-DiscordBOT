from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)


def init_db() -> None:
    # 모델 모듈을 import해야 SQLModel.metadata에 테이블이 등록된다.
    from app.members import models as _members_models  # noqa: F401
    from app.verify import models as _verify_models  # noqa: F401
    from app.settings_kv import models as _settings_models  # noqa: F401
    from app.categories import models as _categories_models  # noqa: F401
    from app.competitions import models as _competitions_models  # noqa: F401
    from app.participation import models as _participation_models  # noqa: F401
    from app.notices import models as _notices_models  # noqa: F401
    from app.points import models as _points_models  # noqa: F401
    from app.member_attributes import models as _member_attributes_models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
