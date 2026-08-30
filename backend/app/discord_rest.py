"""봇 토큰으로 Discord REST API를 직접 호출하는 모듈.

DISCORD_TOKEN이 설정되지 않은 개발 환경에서는 실제 호출 대신 콘솔에 로그만 남기고
그럴싸한 더미 값을 반환하는 목(mock) 모드로 동작해서, 실제 디스코드 서버 없이도
나머지 기능을 개발/테스트할 수 있게 한다.
"""

import itertools

import httpx

from app.core.config import settings

DISCORD_API = "https://discord.com/api/v10"

_mock_id_counter = itertools.count(1)


def _mock_id() -> str:
    return f"mock-{next(_mock_id_counter)}"


def _headers() -> dict:
    return {
        "Authorization": f"Bot {settings.discord_token}",
        "Content-Type": "application/json",
    }


async def list_roles(guild_id: str) -> list[dict]:
    if not settings.discord_configured:
        print(f"[discord_rest:mock] list_roles(guild_id={guild_id})")
        return [{"id": "mock-role-1", "name": "부원(mock)"}]
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{DISCORD_API}/guilds/{guild_id}/roles", headers=_headers())
        resp.raise_for_status()
        return [{"id": r["id"], "name": r["name"]} for r in resp.json()]


async def create_role(guild_id: str, name: str) -> str:
    if not settings.discord_configured:
        rid = _mock_id()
        print(f"[discord_rest:mock] create_role(name={name!r}) -> {rid}")
        return rid
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{DISCORD_API}/guilds/{guild_id}/roles", headers=_headers(), json={"name": name[:100]}
        )
        resp.raise_for_status()
        return resp.json()["id"]


async def list_channels(guild_id: str) -> list[dict]:
    if not settings.discord_configured:
        print(f"[discord_rest:mock] list_channels(guild_id={guild_id})")
        return [{"id": "mock-channel-1", "name": "공지(mock)", "type": 0, "parent_id": None}]
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{DISCORD_API}/guilds/{guild_id}/channels", headers=_headers())
        resp.raise_for_status()
        return [
            {"id": c["id"], "name": c["name"], "type": c["type"], "parent_id": c.get("parent_id")}
            for c in resp.json()
        ]


async def get_member_role_ids(guild_id: str, user_id: str) -> list[str]:
    if not settings.discord_configured:
        print(f"[discord_rest:mock] get_member_role_ids(guild_id={guild_id}, user_id={user_id})")
        return []
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{DISCORD_API}/guilds/{guild_id}/members/{user_id}", headers=_headers()
        )
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        return resp.json().get("roles", [])


async def grant_role(guild_id: str, user_id: str, role_id: str) -> None:
    if not settings.discord_configured:
        print(f"[discord_rest:mock] grant_role(user={user_id}, role={role_id})")
        return
    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{DISCORD_API}/guilds/{guild_id}/members/{user_id}/roles/{role_id}",
            headers=_headers(),
        )
        if resp.status_code not in (200, 201, 204):
            raise RuntimeError(f"역할 부여 실패 (user={user_id}, role={role_id}): {resp.text}")


async def revoke_role(guild_id: str, user_id: str, role_id: str) -> None:
    if not settings.discord_configured:
        print(f"[discord_rest:mock] revoke_role(user={user_id}, role={role_id})")
        return
    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{DISCORD_API}/guilds/{guild_id}/members/{user_id}/roles/{role_id}",
            headers=_headers(),
        )
        if resp.status_code not in (200, 204, 404):
            raise RuntimeError(f"역할 해제 실패 (user={user_id}, role={role_id}): {resp.text}")


async def delete_role(guild_id: str, role_id: str) -> None:
    """대회 삭제 등 정리(cleanup) 용도라, 실패해도 예외를 던지지 않고 로그만 남긴다."""
    if not settings.discord_configured:
        print(f"[discord_rest:mock] delete_role(role={role_id})")
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.delete(
                f"{DISCORD_API}/guilds/{guild_id}/roles/{role_id}", headers=_headers()
            )
            if resp.status_code not in (200, 204, 404):
                print(f"[discord_rest] 역할 삭제 실패 (role={role_id}): {resp.text}")
    except httpx.HTTPError as exc:
        print(f"[discord_rest] 역할 삭제 중 네트워크 오류 (role={role_id}): {exc!r}")


async def set_nickname(guild_id: str, user_id: str, nickname: str) -> None:
    if not settings.discord_configured:
        print(f"[discord_rest:mock] set_nickname(user={user_id}, nickname={nickname!r})")
        return
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{DISCORD_API}/guilds/{guild_id}/members/{user_id}",
            headers=_headers(),
            json={"nick": nickname[:32]},
        )
        if resp.status_code not in (200, 204):
            raise RuntimeError(f"닉네임 변경 실패 (user={user_id}): {resp.text}")


VIEW_CHANNEL = 1 << 10


def private_to_role_overwrites(guild_id: str, role_id: str) -> list[dict]:
    """@everyone에게는 안 보이고, 지정한 역할만 볼 수 있게 하는 permission_overwrites."""
    return [
        {"id": guild_id, "type": 0, "deny": str(VIEW_CHANNEL), "allow": "0"},
        {"id": role_id, "type": 0, "allow": str(VIEW_CHANNEL), "deny": "0"},
    ]


async def create_channel(
    guild_id: str,
    name: str,
    parent_id: str | None = None,
    channel_type: int = 0,
    permission_overwrites: list[dict] | None = None,
) -> str:
    if not settings.discord_configured:
        cid = _mock_id()
        print(f"[discord_rest:mock] create_channel(name={name!r}) -> {cid}")
        return cid
    payload: dict = {"name": name[:100], "type": channel_type}
    if parent_id:
        payload["parent_id"] = parent_id
    if permission_overwrites is not None:
        payload["permission_overwrites"] = permission_overwrites
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{DISCORD_API}/guilds/{guild_id}/channels", headers=_headers(), json=payload
        )
        resp.raise_for_status()
        return resp.json()["id"]


async def delete_channel(channel_id: str) -> None:
    """대회 삭제 등 정리(cleanup) 용도라, 실패해도 예외를 던지지 않고 로그만 남긴다."""
    if not settings.discord_configured:
        print(f"[discord_rest:mock] delete_channel(channel={channel_id})")
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.delete(f"{DISCORD_API}/channels/{channel_id}", headers=_headers())
            if resp.status_code not in (200, 204, 404):
                print(f"[discord_rest] 채널 삭제 실패 (channel={channel_id}): {resp.text}")
    except httpx.HTTPError as exc:
        print(f"[discord_rest] 채널 삭제 중 네트워크 오류 (channel={channel_id}): {exc!r}")


async def send_message(
    channel_id: str, embed: dict | None = None, components: list | None = None, content: str | None = None
) -> str:
    if not settings.discord_configured:
        mid = _mock_id()
        print(f"[discord_rest:mock] send_message(channel={channel_id}) -> {mid}")
        return mid
    payload: dict = {}
    if content:
        payload["content"] = content
    if embed:
        payload["embeds"] = [embed]
    if components:
        payload["components"] = components
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{DISCORD_API}/channels/{channel_id}/messages", headers=_headers(), json=payload
        )
        resp.raise_for_status()
        return resp.json()["id"]


async def edit_message(
    channel_id: str, message_id: str, embed: dict | None = None, components: list | None = None
) -> None:
    if not settings.discord_configured:
        print(f"[discord_rest:mock] edit_message(channel={channel_id}, message={message_id})")
        return
    payload: dict = {}
    if embed is not None:
        payload["embeds"] = [embed]
    if components is not None:
        payload["components"] = components
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{DISCORD_API}/channels/{channel_id}/messages/{message_id}",
            headers=_headers(),
            json=payload,
        )
        resp.raise_for_status()


async def delete_message(channel_id: str, message_id: str) -> None:
    """공지 삭제 등 정리(cleanup) 용도라, 실패해도 예외를 던지지 않고 로그만 남긴다."""
    if not settings.discord_configured:
        print(f"[discord_rest:mock] delete_message(channel={channel_id}, message={message_id})")
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.delete(
                f"{DISCORD_API}/channels/{channel_id}/messages/{message_id}", headers=_headers()
            )
            if resp.status_code not in (200, 204, 404):
                print(f"[discord_rest] 메시지 삭제 실패 (channel={channel_id}, message={message_id}): {resp.text}")
    except httpx.HTTPError as exc:
        print(f"[discord_rest] 메시지 삭제 중 네트워크 오류 (channel={channel_id}): {exc!r}")


async def send_dm(user_id: str, content: str) -> None:
    """DM은 항상 '베스트 에포트'다 — 유저가 DM을 막아뒀거나 타임아웃이 나도
    호출부(참가 처리 등)의 핵심 로직을 절대 실패시키면 안 된다."""
    if not settings.discord_configured:
        print(f"[discord_rest:mock] send_dm(user={user_id}, content={content!r})")
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            dm = await client.post(
                f"{DISCORD_API}/users/@me/channels", headers=_headers(), json={"recipient_id": user_id}
            )
            dm.raise_for_status()
            dm_channel_id = dm.json()["id"]
            resp = await client.post(
                f"{DISCORD_API}/channels/{dm_channel_id}/messages",
                headers=_headers(),
                json={"content": content},
            )
            if resp.status_code not in (200, 201):
                print(f"[discord_rest] DM 발송 실패 (user={user_id}): {resp.text}")
    except httpx.HTTPError as exc:
        print(f"[discord_rest] DM 발송 중 네트워크 오류 (user={user_id}): {exc!r}")
