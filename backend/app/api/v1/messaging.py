from app.schemas.outputs import MessageOut
from fastapi import APIRouter, Query, Request
from sqlalchemy import select, func, exists, or_, and_
from app.core.dependencies import DB, CurrentUser, CSRF
from app.models import Conversation, ConversationMember, Message, Block, User, now
from app.policies.access import conversation_access
from app.schemas.inputs import ConversationInput, MessageInput
from app.repositories.common import paginate
from app.services.presenters import user_summary
from app.services.messages import start_conversation, send_message, message_summary
from app.middleware.rate_limit import rate

router = APIRouter(prefix="/conversations", tags=["Messages"])


@router.get("")
def conversations(db: DB, user: CurrentUser, cursor: str | None = None, limit: int = Query(30, ge=1, le=50)):
    blocked_other = (
        select(ConversationMember.conversation_id)
        .join(User, User.id == ConversationMember.user_id)
        .where(
            or_(
                User.is_suspended.is_(True),
                exists().where(
                    or_(
                        and_(Block.user_id == user.id, Block.target_id == ConversationMember.user_id),
                        and_(Block.target_id == user.id, Block.user_id == ConversationMember.user_id),
                    )
                ),
            )
        )
    )
    stmt = (
        select(Conversation)
        .join(ConversationMember)
        .where(ConversationMember.user_id == user.id, Conversation.id.not_in(blocked_other))
    )
    rows, nxt = paginate(db, stmt, Conversation, cursor, limit)
    ids = [r.id for r in rows]
    ranked = (
        select(
            Message.id,
            func.row_number()
            .over(partition_by=Message.conversation_id, order_by=[Message.created_at.desc(), Message.id.desc()])
            .label("rank"),
        )
        .where(Message.conversation_id.in_(ids))
        .subquery()
    )
    latest = {
        m.conversation_id: m
        for m in db.scalars(select(Message).join(ranked, ranked.c.id == Message.id).where(ranked.c.rank == 1))
    }
    unread = dict(
        db.execute(
            select(Message.conversation_id, func.count())
            .join(ConversationMember, ConversationMember.conversation_id == Message.conversation_id)
            .where(
                Message.conversation_id.in_(ids),
                ConversationMember.user_id == user.id,
                Message.sender_id != user.id,
                Message.created_at > ConversationMember.last_read_at,
            )
            .group_by(Message.conversation_id)
        ).all()
    )
    return {
        "items": [
            {
                "id": r.id,
                "members": [user_summary(m.user) for m in r.members],
                "last_message": message_summary(latest[r.id]) if r.id in latest else None,
                "unread_count": unread.get(r.id, 0),
            }
            for r in rows
        ],
        "next_cursor": nxt,
    }


@router.post("", status_code=201, dependencies=[CSRF])
def create(data: ConversationInput, db: DB, user: CurrentUser, request: Request):
    rate(request, "conversations", 20, user.id)
    return start_conversation(db, user.id, str(data.user_id))


@router.get("/{id_}/messages")
def history(id_: str, db: DB, user: CurrentUser, cursor: str | None = None, limit: int = Query(30, ge=1, le=50)):
    members = conversation_access(db, id_, user.id)
    rows, nxt = paginate(db, select(Message).where(Message.conversation_id == id_), Message, cursor, limit)
    return {
        "items": [message_summary(r) for r in rows],
        "next_cursor": nxt,
        "members": [{"user": user_summary(m.user), "last_read_at": m.last_read_at} for m in members],
    }


@router.post("/{id_}/messages", status_code=201, dependencies=[CSRF], response_model=MessageOut)
def send(id_: str, data: MessageInput, db: DB, user: CurrentUser, request: Request):
    rate(request, "messages", 60, user.id)
    return send_message(db, id_, user.id, data)


@router.post("/{id_}/read", dependencies=[CSRF])
def read(id_: str, db: DB, user: CurrentUser):
    members = conversation_access(db, id_, user.id)
    for m in members:
        if m.user_id == user.id:
            m.last_read_at = now()
    return {"ok": True}
