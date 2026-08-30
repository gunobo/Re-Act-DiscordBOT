import json

from sqlmodel import Session, select

from app.settings_kv.models import AppSetting

DEFAULT_NICKNAME_FORMAT = "{student_id} {name}"

KEY_VERIFIED_ROLE_IDS = "verified_role_ids"
KEY_NICKNAME_FORMAT = "nickname_format"
KEY_ADMIN_ROLE_ID = "admin_role_id"
KEY_NOTICE_CHANNEL_ID = "notice_channel_id"
KEY_COMPETITION_PARENT_CHANNEL_ID = "competition_parent_channel_id"


def get_raw(session: Session, key: str, default: str = "") -> str:
    row = session.get(AppSetting, key)
    return row.value if row else default


def set_raw(session: Session, key: str, value: str) -> None:
    row = session.get(AppSetting, key)
    if row:
        row.value = value
    else:
        row = AppSetting(key=key, value=value)
    session.add(row)
    session.commit()


def get_verified_role_ids(session: Session) -> list[str]:
    raw = get_raw(session, KEY_VERIFIED_ROLE_IDS, "[]")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def set_verified_role_ids(session: Session, role_ids: list[str]) -> None:
    set_raw(session, KEY_VERIFIED_ROLE_IDS, json.dumps(role_ids))


def get_nickname_format(session: Session) -> str:
    return get_raw(session, KEY_NICKNAME_FORMAT, DEFAULT_NICKNAME_FORMAT)


def set_nickname_format(session: Session, fmt: str) -> None:
    set_raw(session, KEY_NICKNAME_FORMAT, fmt)


def get_admin_role_id(session: Session) -> str | None:
    return get_raw(session, KEY_ADMIN_ROLE_ID, "") or None


def set_admin_role_id(session: Session, role_id: str | None) -> None:
    set_raw(session, KEY_ADMIN_ROLE_ID, role_id or "")


def get_notice_channel_id(session: Session) -> str | None:
    return get_raw(session, KEY_NOTICE_CHANNEL_ID, "") or None


def set_notice_channel_id(session: Session, channel_id: str | None) -> None:
    set_raw(session, KEY_NOTICE_CHANNEL_ID, channel_id or "")


def get_competition_parent_channel_id(session: Session) -> str | None:
    return get_raw(session, KEY_COMPETITION_PARENT_CHANNEL_ID, "") or None


def set_competition_parent_channel_id(session: Session, channel_id: str | None) -> None:
    set_raw(session, KEY_COMPETITION_PARENT_CHANNEL_ID, channel_id or "")
