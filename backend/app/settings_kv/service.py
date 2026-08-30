import json

from sqlmodel import Session, select

from app.settings_kv.models import AppSetting

DEFAULT_NICKNAME_FORMAT = "{student_id} {name}"

KEY_VERIFIED_ROLE_IDS = "verified_role_ids"
KEY_NICKNAME_FORMAT = "nickname_format"
KEY_ADMIN_ROLE_ID = "admin_role_id"
KEY_NOTICE_CHANNEL_ID = "notice_channel_id"
KEY_JOIN_CHANNEL_ID = "join_channel_id"
KEY_POINTS_PER_JOIN = "points_per_join"
KEY_GITHUB_CHANNEL_ID = "github_channel_id"

DEFAULT_POINTS_PER_JOIN = 10


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


def get_join_channel_id(session: Session) -> str | None:
    return get_raw(session, KEY_JOIN_CHANNEL_ID, "") or None


def set_join_channel_id(session: Session, channel_id: str | None) -> None:
    set_raw(session, KEY_JOIN_CHANNEL_ID, channel_id or "")


def get_points_per_join(session: Session) -> int:
    try:
        return int(get_raw(session, KEY_POINTS_PER_JOIN, str(DEFAULT_POINTS_PER_JOIN)))
    except ValueError:
        return DEFAULT_POINTS_PER_JOIN


def set_points_per_join(session: Session, points: int) -> None:
    set_raw(session, KEY_POINTS_PER_JOIN, str(points))


def get_github_channel_id(session: Session) -> str | None:
    return get_raw(session, KEY_GITHUB_CHANNEL_ID, "") or None


def set_github_channel_id(session: Session, channel_id: str | None) -> None:
    set_raw(session, KEY_GITHUB_CHANNEL_ID, channel_id or "")
