from datetime import datetime
from pathlib import Path

import csv
import io

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, func, select

from app import discord_rest
from app.categories import service as categories_service
from app.categories.models import DEFAULT_TEMPLATE_TEXT
from app.competitions import service as competitions_service
from app.core.config import settings
from app.core.session_auth import get_current_admin, require_admin
from app.db.session import get_session
from app.member_attributes import service as attributes_service
from app.members import service as members_service
from app.members.models import Member
from app.notices import service as notices_service
from app.participation.models import Participation
from app.points import service as points_service
from app.settings_kv import service as settings_service

router = APIRouter()

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

_STATIC_DIR = Path(__file__).parent / "static"


def _static_version() -> str:
    """정적 파일(CSS/JS)이 바뀔 때마다 캐시를 무력화하기 위한 버전 문자열.
    빌드마다(파일 mtime 기준) 바뀌므로 브라우저/Cloudflare 엣지 캐시에 옛날
    style.css가 남아있는 문제를 막아준다."""
    try:
        newest = max(f.stat().st_mtime for f in _STATIC_DIR.rglob("*") if f.is_file())
        return str(int(newest))
    except ValueError:
        return "0"


STATIC_VERSION = _static_version()


def render(request: Request, name: str, **ctx):
    ctx.setdefault("admin", get_current_admin(request))
    ctx.setdefault("static_version", STATIC_VERSION)
    return templates.TemplateResponse(request, name, ctx)


# ---------- 공개 페이지 ----------


@router.get("/")
def home(request: Request):
    return render(request, "home.html")


@router.get("/notices")
def public_notices(request: Request, session: Session = Depends(get_session)):
    notices = notices_service.list_notices(session, published_only=True)
    return render(request, "public_notices.html", notices=notices)


@router.get("/notices/{notice_id}")
def public_notice_detail(notice_id: int, request: Request, session: Session = Depends(get_session)):
    notice = notices_service.get_notice(session, notice_id)
    if not notice or not notice.published:
        raise HTTPException(status_code=404)
    content_html = notices_service.render_markdown(notice.content)
    return render(request, "notice_detail.html", notice=notice, content_html=content_html)


# ---------- 관리자 대시보드 ----------


@router.get("/admin")
def admin_dashboard(
    request: Request, admin: dict = Depends(require_admin), session: Session = Depends(get_session)
):
    return render(
        request,
        "admin_dashboard.html",
        allowed_count=len(members_service.list_allowed_members(session)),
        member_count=len(members_service.list_members(session)),
        competition_count=len(competitions_service.list_competitions(session)),
        category_count=len(categories_service.list_categories(session)),
        notice_count=len(notices_service.list_notices(session)),
        published_notice_count=len(notices_service.list_notices(session, published_only=True)),
        discord_configured=settings.discord_configured,
    )


# ---------- 부원 관리 ----------


@router.get("/admin/members")
def admin_members(
    request: Request, admin: dict = Depends(require_admin), session: Session = Depends(get_session)
):
    members = members_service.list_members(session)
    verified_emails = {m.email for m in members}
    return render(
        request,
        "members.html",
        allowed_members=members_service.list_allowed_members(session),
        members=members,
        verified_emails=verified_emails,
        attribute_definitions=attributes_service.list_definitions(session),
    )


@router.post("/admin/members/add")
def admin_members_add(
    email: str = Form(...),
    student_id: str = Form(...),
    name: str = Form(...),
    admin: dict = Depends(require_admin),
    session: Session = Depends(get_session),
):
    members_service.add_allowed_member(session, email, student_id, name, admin["discord_id"])
    return RedirectResponse(url="/admin/members", status_code=303)


@router.post("/admin/members/delete")
def admin_members_delete(
    email: str = Form(...),
    admin: dict = Depends(require_admin),
    session: Session = Depends(get_session),
):
    members_service.delete_allowed_member(session, email)
    return RedirectResponse(url="/admin/members", status_code=303)


@router.post("/admin/members/unverify")
async def admin_members_unverify(
    discord_id: str = Form(...),
    admin: dict = Depends(require_admin),
    session: Session = Depends(get_session),
):
    role_ids = settings_service.get_verified_role_ids(session)
    for role_id in role_ids:
        try:
            await discord_rest.revoke_role(settings.discord_guild_id, discord_id, role_id)
        except Exception:  # noqa: BLE001 - 역할 해제 실패해도 인증 데이터는 정리한다
            pass
    members_service.delete_member(session, discord_id)
    return RedirectResponse(url="/admin/members", status_code=303)


# ---------- 부원 속성 (디스코드에는 반영되지 않는 내부 기록용 항목) ----------


@router.get("/admin/attributes")
def admin_attributes(
    request: Request, admin: dict = Depends(require_admin), session: Session = Depends(get_session)
):
    return render(request, "attributes.html", definitions=attributes_service.list_definitions(session))


@router.post("/admin/attributes/add")
def admin_attributes_add(
    name: str = Form(...), admin: dict = Depends(require_admin), session: Session = Depends(get_session)
):
    attributes_service.create_definition(session, name)
    return RedirectResponse(url="/admin/attributes", status_code=303)


@router.post("/admin/attributes/delete/{definition_id}")
def admin_attributes_delete(
    definition_id: int, admin: dict = Depends(require_admin), session: Session = Depends(get_session)
):
    attributes_service.delete_definition(session, definition_id)
    return RedirectResponse(url="/admin/attributes", status_code=303)


@router.get("/admin/members/{discord_id}/attributes")
def admin_member_attributes_edit(
    discord_id: str,
    request: Request,
    admin: dict = Depends(require_admin),
    session: Session = Depends(get_session),
):
    member = members_service.get_member(session, discord_id)
    if not member:
        raise HTTPException(status_code=404)
    return render(
        request,
        "member_attributes_edit.html",
        member=member,
        definitions=attributes_service.list_definitions(session),
        values=attributes_service.get_values_for_member(session, discord_id),
    )


@router.post("/admin/members/{discord_id}/attributes")
async def admin_member_attributes_save(
    discord_id: str,
    request: Request,
    admin: dict = Depends(require_admin),
    session: Session = Depends(get_session),
):
    form = await request.form()
    for definition in attributes_service.list_definitions(session):
        attributes_service.set_value(
            session, discord_id, definition.id, form.get(f"attr_{definition.id}", "")
        )
    return RedirectResponse(url="/admin/members", status_code=303)


# ---------- 설정 ----------


@router.get("/admin/settings")
async def admin_settings(
    request: Request, admin: dict = Depends(require_admin), session: Session = Depends(get_session)
):
    roles = await discord_rest.list_roles(settings.discord_guild_id)
    channels = await discord_rest.list_channels(settings.discord_guild_id)
    return render(
        request,
        "settings.html",
        roles=roles,
        text_channels=[c for c in channels if c["type"] == 0],
        verified_role_ids=settings_service.get_verified_role_ids(session),
        nickname_format=settings_service.get_nickname_format(session),
        admin_role_id=settings_service.get_admin_role_id(session),
        notice_channel_id=settings_service.get_notice_channel_id(session),
        join_channel_id=settings_service.get_join_channel_id(session),
        points_per_join=settings_service.get_points_per_join(session),
        github_channel_id=settings_service.get_github_channel_id(session),
        github_webhook_configured=bool(settings.github_webhook_secret),
        web_base_url=settings.web_base_url,
        discord_configured=settings.discord_configured,
    )


@router.post("/admin/settings")
async def admin_settings_save(
    request: Request, admin: dict = Depends(require_admin), session: Session = Depends(get_session)
):
    form = await request.form()
    settings_service.set_verified_role_ids(session, form.getlist("verified_role_ids"))
    settings_service.set_nickname_format(
        session, form.get("nickname_format") or settings_service.DEFAULT_NICKNAME_FORMAT
    )
    settings_service.set_admin_role_id(session, form.get("admin_role_id") or None)
    settings_service.set_notice_channel_id(session, form.get("notice_channel_id") or None)
    settings_service.set_join_channel_id(session, form.get("join_channel_id") or None)
    try:
        points_per_join = int(form.get("points_per_join") or settings_service.DEFAULT_POINTS_PER_JOIN)
    except ValueError:
        points_per_join = settings_service.DEFAULT_POINTS_PER_JOIN
    settings_service.set_points_per_join(session, points_per_join)
    settings_service.set_github_channel_id(session, form.get("github_channel_id") or None)
    return RedirectResponse(url="/admin/settings", status_code=303)


# ---------- 카테고리 템플릿 ----------


@router.get("/admin/categories")
def admin_categories(
    request: Request, admin: dict = Depends(require_admin), session: Session = Depends(get_session)
):
    categories = categories_service.list_categories(session)
    channel_counts = {
        c.id: len(categories_service.list_channels_for_template(session, c.id)) for c in categories
    }
    return render(request, "categories.html", categories=categories, channel_counts=channel_counts)


@router.post("/admin/categories/add")
def admin_categories_add(
    name: str = Form(...), admin: dict = Depends(require_admin), session: Session = Depends(get_session)
):
    categories_service.create_category(session, name)
    return RedirectResponse(url="/admin/categories", status_code=303)


@router.post("/admin/categories/update/{category_id}")
def admin_categories_update(
    category_id: int,
    name: str = Form(...),
    admin: dict = Depends(require_admin),
    session: Session = Depends(get_session),
):
    categories_service.update_category(session, category_id, name)
    return RedirectResponse(url="/admin/categories", status_code=303)


@router.post("/admin/categories/delete/{category_id}")
def admin_categories_delete(
    category_id: int, admin: dict = Depends(require_admin), session: Session = Depends(get_session)
):
    categories_service.delete_category(session, category_id)
    return RedirectResponse(url="/admin/categories", status_code=303)


@router.get("/admin/categories/{category_id}")
def admin_category_detail(
    category_id: int,
    request: Request,
    admin: dict = Depends(require_admin),
    session: Session = Depends(get_session),
):
    category = categories_service.get_category(session, category_id)
    if not category:
        raise HTTPException(status_code=404)
    return render(
        request,
        "category_detail.html",
        category=category,
        channels=categories_service.list_channels_for_template(session, category_id),
        default_template=DEFAULT_TEMPLATE_TEXT,
    )


@router.post("/admin/categories/{category_id}/channels/add")
def admin_category_channel_add(
    category_id: int,
    name: str = Form(...),
    template_text: str = Form(""),
    is_join_channel: bool = Form(False),
    is_public: bool = Form(False),
    channel_type: int = Form(0),
    admin: dict = Depends(require_admin),
    session: Session = Depends(get_session),
):
    categories_service.add_channel(
        session, category_id, name, template_text, is_join_channel, is_public, channel_type
    )
    return RedirectResponse(url=f"/admin/categories/{category_id}", status_code=303)


@router.post("/admin/categories/{category_id}/channels/{channel_id}/update")
def admin_category_channel_update(
    category_id: int,
    channel_id: int,
    name: str = Form(...),
    template_text: str = Form(""),
    is_join_channel: bool = Form(False),
    is_public: bool = Form(False),
    channel_type: int = Form(0),
    admin: dict = Depends(require_admin),
    session: Session = Depends(get_session),
):
    categories_service.update_channel(
        session, channel_id, name, template_text, is_join_channel, is_public, channel_type
    )
    return RedirectResponse(url=f"/admin/categories/{category_id}", status_code=303)


@router.post("/admin/categories/{category_id}/channels/{channel_id}/delete")
def admin_category_channel_delete(
    category_id: int,
    channel_id: int,
    admin: dict = Depends(require_admin),
    session: Session = Depends(get_session),
):
    categories_service.delete_channel(session, channel_id)
    return RedirectResponse(url=f"/admin/categories/{category_id}", status_code=303)


# ---------- 대회 ----------


@router.get("/admin/competitions")
def admin_competitions(
    request: Request, admin: dict = Depends(require_admin), session: Session = Depends(get_session)
):
    return render(request, "competitions.html", competitions=competitions_service.list_competitions(session))


@router.get("/admin/competitions/new")
def admin_competitions_new(
    request: Request, admin: dict = Depends(require_admin), session: Session = Depends(get_session)
):
    categories = categories_service.list_categories(session)
    channel_counts = {
        c.id: len(categories_service.list_channels_for_template(session, c.id)) for c in categories
    }
    return render(
        request, "competition_new.html", categories=categories, channel_counts=channel_counts
    )


@router.post("/admin/competitions/new")
async def admin_competitions_create(
    request: Request, admin: dict = Depends(require_admin), session: Session = Depends(get_session)
):
    form = await request.form()
    title = form.get("title", "").strip()
    description = form.get("description", "").strip()
    deadline = datetime.fromisoformat(form.get("deadline"))

    selections = []
    for category in categories_service.list_categories(session):
        if form.get(f"cat_{category.id}_selected"):
            capacity_raw = form.get(f"cat_{category.id}_capacity") or "0"
            selections.append(
                {
                    "category_template_id": category.id,
                    "name": category.name,
                    "capacity": max(1, int(capacity_raw)),
                }
            )

    if selections:
        await competitions_service.create_competition(
            session, title, description, deadline, selections, admin["discord_id"]
        )
    return RedirectResponse(url="/admin/competitions", status_code=303)


@router.get("/admin/competitions/{competition_id}")
def admin_competition_detail(
    competition_id: int,
    request: Request,
    admin: dict = Depends(require_admin),
    session: Session = Depends(get_session),
):
    competition = competitions_service.get_competition(session, competition_id)
    if not competition:
        raise HTTPException(status_code=404)
    comp_categories = competitions_service.list_categories_for_competition(session, competition_id)
    category_counts = []
    for cc in comp_categories:
        count = session.exec(
            select(func.count()).select_from(Participation).where(
                Participation.competition_category_id == cc.id
            )
        ).one()
        channels = competitions_service.list_channels_for_category(session, cc.id)
        category_counts.append((cc, count, channels))
    return render(
        request,
        "competition_detail.html",
        competition=competition,
        category_counts=category_counts,
        attribute_definitions=attributes_service.list_definitions(session),
    )


@router.post("/admin/competitions/{competition_id}/delete")
async def admin_competition_delete(
    competition_id: int, admin: dict = Depends(require_admin), session: Session = Depends(get_session)
):
    await competitions_service.delete_competition(session, competition_id)
    return RedirectResponse(url="/admin/competitions", status_code=303)


@router.get("/admin/competitions/{competition_id}/export.csv")
def admin_competition_export_csv(
    competition_id: int,
    request: Request,
    admin: dict = Depends(require_admin),
    session: Session = Depends(get_session),
):
    competition = competitions_service.get_competition(session, competition_id)
    if not competition:
        raise HTTPException(status_code=404)

    attr_ids = [int(v) for v in request.query_params.getlist("attr_ids") if v.isdigit()]
    definitions = [
        d for d in attributes_service.list_definitions(session) if d.id in attr_ids
    ]
    attribute_values = attributes_service.get_values_map(session, attr_ids)

    comp_categories = competitions_service.list_categories_for_competition(session, competition_id)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["카테고리", "학번", "이름", "디스코드ID", "참가일시"] + [d.name for d in definitions]
    )
    for cc in comp_categories:
        rows = session.exec(
            select(Participation, Member)
            .join(Member, Member.discord_id == Participation.discord_id)
            .where(Participation.competition_category_id == cc.id)
            .order_by(Participation.joined_at)
        ).all()
        for participation, member in rows:
            extra_columns = [
                attribute_values.get((member.discord_id, d.id), "") for d in definitions
            ]
            writer.writerow(
                [
                    cc.name,
                    member.student_id,
                    member.name,
                    member.discord_id,
                    participation.joined_at.strftime("%Y-%m-%d %H:%M"),
                ]
                + extra_columns
            )

    csv_bytes = "﻿" + buffer.getvalue()  # 엑셀 한글 깨짐 방지용 BOM
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=competition_{competition_id}_participants.csv"},
    )


# ---------- 포인트/랭킹 ----------


@router.get("/admin/points")
def admin_points(
    request: Request, admin: dict = Depends(require_admin), session: Session = Depends(get_session)
):
    return render(
        request,
        "points.html",
        leaderboard=points_service.list_all_with_totals(session),
        points_per_join=settings_service.get_points_per_join(session),
        transactions=points_service.list_recent_transactions_all(session),
    )


@router.post("/admin/points/award")
def admin_points_award(
    discord_id: str = Form(...),
    points: int = Form(...),
    reason: str = Form(...),
    admin: dict = Depends(require_admin),
    session: Session = Depends(get_session),
):
    points_service.add_points(session, discord_id, points, reason, admin["discord_id"])
    return RedirectResponse(url="/admin/points", status_code=303)


@router.post("/admin/points/delete/{transaction_id}")
def admin_points_delete(
    transaction_id: int, admin: dict = Depends(require_admin), session: Session = Depends(get_session)
):
    points_service.delete_transaction(session, transaction_id)
    return RedirectResponse(url="/admin/points", status_code=303)


# ---------- 공지 ----------


@router.get("/admin/notices")
def admin_notices(
    request: Request, admin: dict = Depends(require_admin), session: Session = Depends(get_session)
):
    return render(request, "admin_notices.html", notices=notices_service.list_notices(session))


@router.get("/admin/notices/new")
def admin_notices_new(request: Request, admin: dict = Depends(require_admin)):
    return render(request, "notice_form.html", notice=None)


@router.post("/admin/notices/new")
def admin_notices_create(
    title: str = Form(...),
    content: str = Form(...),
    admin: dict = Depends(require_admin),
    session: Session = Depends(get_session),
):
    notices_service.create_notice(session, title, content, admin["discord_id"])
    return RedirectResponse(url="/admin/notices", status_code=303)


@router.get("/admin/notices/{notice_id}/edit")
def admin_notices_edit_page(
    notice_id: int,
    request: Request,
    admin: dict = Depends(require_admin),
    session: Session = Depends(get_session),
):
    notice = notices_service.get_notice(session, notice_id)
    if not notice:
        raise HTTPException(status_code=404)
    return render(request, "notice_form.html", notice=notice)


@router.post("/admin/notices/{notice_id}/edit")
def admin_notices_edit(
    notice_id: int,
    title: str = Form(...),
    content: str = Form(...),
    admin: dict = Depends(require_admin),
    session: Session = Depends(get_session),
):
    notices_service.update_notice(session, notice_id, title, content)
    return RedirectResponse(url="/admin/notices", status_code=303)


@router.post("/admin/notices/{notice_id}/publish")
async def admin_notices_publish(
    notice_id: int, admin: dict = Depends(require_admin), session: Session = Depends(get_session)
):
    channel_id = settings_service.get_notice_channel_id(session)
    if channel_id:
        await notices_service.publish_notice(session, notice_id, channel_id)
    return RedirectResponse(url="/admin/notices", status_code=303)


@router.post("/admin/notices/{notice_id}/delete")
async def admin_notices_delete(
    notice_id: int, admin: dict = Depends(require_admin), session: Session = Depends(get_session)
):
    await notices_service.delete_notice(session, notice_id)
    return RedirectResponse(url="/admin/notices", status_code=303)
