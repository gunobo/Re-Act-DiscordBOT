import hashlib
import hmac

EMBED_COLOR_OPEN = 0x2DA44E
EMBED_COLOR_CLOSED = 0x8250DF
EMBED_COLOR_MERGED = 0x8250DF


def verify_signature(secret: str, payload_body: bytes, signature_header: str | None) -> bool:
    if not secret:
        # 시크릿을 설정하지 않았으면 검증을 건너뛴다 (개발 초기 단계용).
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), payload_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature_header)


def build_embed(event: str, payload: dict) -> dict | None:
    repo_name = payload.get("repository", {}).get("full_name", "unknown/repo")

    if event == "pull_request":
        action = payload.get("action")
        if action not in ("opened", "closed", "reopened"):
            return None
        pr = payload["pull_request"]
        merged = pr.get("merged", False)
        if action == "closed" and merged:
            status, color = "머지됨", EMBED_COLOR_MERGED
        elif action == "closed":
            status, color = "닫힘", EMBED_COLOR_CLOSED
        else:
            status, color = "열림", EMBED_COLOR_OPEN
        return {
            "title": f"[{repo_name}] PR #{pr['number']}: {pr['title']}",
            "url": pr["html_url"],
            "description": f"상태: {status}",
            "color": color,
            "footer": {"text": f"by {pr['user']['login']}"},
        }

    if event == "issues":
        action = payload.get("action")
        if action not in ("opened", "closed", "reopened"):
            return None
        issue = payload["issue"]
        status, color = ("닫힘", EMBED_COLOR_CLOSED) if action == "closed" else ("열림", EMBED_COLOR_OPEN)
        return {
            "title": f"[{repo_name}] Issue #{issue['number']}: {issue['title']}",
            "url": issue["html_url"],
            "description": f"상태: {status}",
            "color": color,
            "footer": {"text": f"by {issue['user']['login']}"},
        }

    return None
