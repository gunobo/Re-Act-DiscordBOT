from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, func, select

from app import discord_rest
from app.categories import service as categories_service
from app.categories.models import DEFAULT_TEMPLATE_TEXT
from app.competitions import service as competitions_service
from app.core.config import settings
from app.core.session_auth import get_current_admin, require_admin
from app.db.session import get_session
from app.members import service as members_service
from app.notices import service as notices_service
from app.participation.models import Participation
from app.settings_kv import service as settings_service

router = APIRouter()

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def render(request: Request, name: str, **ctx):
    ctx.setdefault("admin", get_current_admin(request))
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
    return render(request, "notice_detail.html", notice=notice)


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
        category_channels=[c for c in channels if c["type"] == 4],
        verified_role_ids=settings_service.get_verified_role_ids(session),
        nickname_format=settings_service.get_nickname_format(session),
        admin_role_id=settings_service.get_admin_role_id(session),
        notice_channel_id=settings_service.get_notice_channel_id(session),
        competition_parent_channel_id=settings_service.get_competition_parent_channel_id(session),
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
    settings_service.set_competition_parent_channel_id(
        session, form.get("competition_parent_channel_id") or None
    )
    return RedirectResponse(url="/admin/settings", status_code=303)


# ---------- 카테고리 템플릿 ----------


@router.get("/admin/categories")
def admin_categories(
    request: Request, admin: dict = Depends(require_admin), session: Session = Depends(get_session)
):
    return render(
        request,
        "categories.html",
        categories=categories_service.list_categories(session),
        default_template=DEFAULT_TEMPLATE_TEXT,
    )


@router.post("/admin/categories/add")
def admin_categories_add(
    name: str = Form(...),
    template_text: str = Form(...),
    admin: dict = Depends(require_admin),
    session: Session = Depends(get_session),
):
    categories_service.create_category(session, name, template_text)
    return RedirectResponse(url="/admin/categories", status_code=303)


@router.post("/admin/categories/update/{category_id}")
def admin_categories_update(
    category_id: int,
    name: str = Form(...),
    template_text: str = Form(...),
    admin: dict = Depends(require_admin),
    session: Session = Depends(get_session),
):
    categories_service.update_category(session, category_id, name, template_text)
    return RedirectResponse(url="/admin/categories", status_code=303)


@router.post("/admin/categories/delete/{category_id}")
def admin_categories_delete(
    category_id: int, admin: dict = Depends(require_admin), session: Session = Depends(get_session)
):
    categories_service.delete_category(session, category_id)
    return RedirectResponse(url="/admin/categories", status_code=303)


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
    return render(request, "competition_new.html", categories=categories_service.list_categories(session))


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
        category_counts.append((cc, count))
    return render(
        request, "competition_detail.html", competition=competition, category_counts=category_counts
    )


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
def admin_notices_delete(
    notice_id: int, admin: dict = Depends(require_admin), session: Session = Depends(get_session)
):
    notices_service.delete_notice(session, notice_id)
    return RedirectResponse(url="/admin/notices", status_code=303)
