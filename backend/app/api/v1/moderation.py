from fastapi import APIRouter, Query, HTTPException, Request
from sqlalchemy import select, update
from app.core.dependencies import DB, CurrentUser, Admin, CSRF
from app.models import Report, Post, Comment, User, ModerationAction, AuditLog, Session, Media, PostMedia
from app.policies.access import post_access, user_access
from app.schemas.inputs import ReportInput, ActionInput
from app.repositories.common import paginate
from app.middleware.rate_limit import rate

router = APIRouter(tags=["Moderation"])


@router.post("/reports", status_code=201, dependencies=[CSRF])
def report(data: ReportInput, db: DB, user: CurrentUser, request: Request):
    rate(request, "report", 10, user.id)
    target = str(data.target_id)
    if data.target_type == "post":
        post_access(db, target, user.id)
    elif data.target_type == "user":
        user_access(db, target, user.id, private=False)
    else:
        row = db.get(Comment, target)
        if not row:
            raise HTTPException(404, "Comment not found")
        post_access(db, row.post_id, user.id)
        user_access(db, row.author_id, user.id, private=False)
    row = Report(reporter_id=user.id, target_type=data.target_type, target_id=target, reason=data.reason)
    db.add(row)
    db.flush()
    return {"id": row.id, "status": row.status}


@router.get("/admin/reports")
def reports(db: DB, admin: Admin, cursor: str | None = None, limit: int = Query(30, ge=1, le=50), status: str = "open"):
    stmt = select(Report)
    if status != "all":
        stmt = stmt.where(Report.status == status)
    rows, nxt = paginate(db, stmt, Report, cursor, limit)
    return {
        "items": [
            {
                "id": r.id,
                "target_type": r.target_type,
                "target_id": r.target_id,
                "reason": r.reason,
                "status": r.status,
                "created_at": r.created_at,
            }
            for r in rows
        ],
        "next_cursor": nxt,
    }


@router.post("/admin/reports/{id_}/actions", dependencies=[CSRF])
def moderate(id_: str, data: ActionInput, db: DB, admin: Admin):
    report = db.scalar(select(Report).where(Report.id == id_).with_for_update())
    if not report:
        raise HTTPException(404, "Report not found")
    if report.status != "open":
        raise HTTPException(409, "Report already resolved")
    cls = {"post": Post, "comment": Comment, "user": User}[report.target_type]
    target = db.get(cls, report.target_id)
    if data.action == "remove":
        if cls is User:
            raise HTTPException(422, "Use suspend for an account report")
        if target:
            db.delete(target)
    if data.action == "suspend":
        user_id = target.id if cls is User and target else target.author_id if target else None
        user = db.get(User, user_id) if user_id else None
        if not user or user.role == "admin":
            raise HTTPException(422, "Cannot suspend this account")
        user.is_suspended = True
        db.execute(update(Session).where(Session.user_id == user.id).values(revoked=True))
    report.status = "dismissed" if data.action == "dismiss" else "actioned"
    db.add(ModerationAction(report_id=report.id, moderator_id=admin.id, action=data.action, note=data.note))
    db.add(
        AuditLog(
            actor_id=admin.id,
            action=data.action,
            target_id=report.target_id,
            detail={"report_id": report.id, "note": data.note},
        )
    )
    return {"ok": True, "status": report.status}


@router.get("/admin/reports/{id_}/content")
def report_content(id_: str, db: DB, admin: Admin):
    from app.services.presenters import user_summary, posts_summary

    report = db.get(Report, id_)
    if not report:
        raise HTTPException(404, "Report not found")
    cls = {"post": Post, "comment": Comment, "user": User}[report.target_type]
    target = db.get(cls, report.target_id)
    if not target:
        return {"available": False, "message": "Reported content has already been removed"}
    result = {"available": True, "type": report.target_type}
    if cls is Post:
        post = posts_summary(db, [target], admin.id)[0]
        for media in post["media"]:
            media["url"] = f"/api/v1/admin/reports/{report.id}/media/{media['id']}"
        result["post"] = post
    elif cls is Comment:
        result["body"] = target.body
        result["author"] = user_summary(target.author)
    else:
        result["author"] = user_summary(target)
        result["is_suspended"] = target.is_suspended
    db.add(
        AuditLog(
            actor_id=admin.id, action="moderation_review", target_id=report.target_id, detail={"report_id": report.id}
        )
    )
    return result


@router.get("/admin/reports/{id_}/media/{media_id}")
def review_media(id_: str, media_id: str, db: DB, admin: Admin):
    from fastapi.responses import FileResponse, RedirectResponse
    from app.integrations.storage import storage, LocalStorage

    report = db.get(Report, id_)
    if (
        not report
        or report.target_type != "post"
        or not db.scalar(
            select(PostMedia.id).where(PostMedia.post_id == report.target_id, PostMedia.media_id == media_id)
        )
    ):
        raise HTTPException(404, "Reported media not found")
    asset = db.get(Media, media_id)
    store = storage()
    headers = {"Cache-Control": "private, no-store"}
    if isinstance(store, LocalStorage):
        return FileResponse(store.path(asset.object_key), media_type=asset.mime_type, headers=headers)
    return RedirectResponse(store.url(asset.object_key), headers=headers)
