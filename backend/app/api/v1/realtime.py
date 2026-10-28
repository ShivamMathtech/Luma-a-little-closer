import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select, func
from app.core.config import settings
from app.core.security import digest, expired
from app.db.session import SessionLocal
from app.models import Session, User, Notification, Message, ConversationMember

router = APIRouter()


def snapshot(raw):
    with SessionLocal() as db:
        session = db.scalar(select(Session).where(Session.access_hash == digest(raw), Session.revoked.is_(False)))
        if not session or expired(session.access_expires_at) or expired(session.expires_at):
            return None
        user = db.get(User, session.user_id)
        if not user or user.is_suspended:
            return None
        # Only invalidation counters are sent, never message bodies or conversation IDs.
        notifications = db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user.id, Notification.is_read.is_(False))
        )
        messages = db.scalar(
            select(func.count())
            .select_from(Message)
            .join(ConversationMember, ConversationMember.conversation_id == Message.conversation_id)
            .where(
                ConversationMember.user_id == user.id,
                Message.sender_id != user.id,
                Message.created_at > ConversationMember.last_read_at,
            )
        )
        return {"type": "refresh", "notifications": notifications, "messages": messages}


@router.websocket("/ws")
async def websocket(ws: WebSocket):
    if ws.headers.get("origin") not in settings.origins:
        await ws.close(code=4403)
        return
    raw = ws.cookies.get("luma_access", "")
    state = await asyncio.to_thread(snapshot, raw)
    if state is None:
        await ws.close(code=4401)
        return
    await ws.accept()
    try:
        while True:
            await ws.send_json(state)
            try:
                # Client protocol accepts only a bounded text ping. Writes use validated REST endpoints.
                incoming = await asyncio.wait_for(ws.receive_text(), timeout=3)
                if incoming != "ping":
                    await ws.close(code=4400)
                    return
                await asyncio.sleep(1)
            except asyncio.TimeoutError:
                pass
            state = await asyncio.to_thread(snapshot, raw)
            if state is None:
                await ws.close(code=4401)
                return
    except WebSocketDisconnect:
        pass
