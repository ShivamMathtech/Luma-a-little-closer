from fastapi import HTTPException
from sqlalchemy import select
from app.models import Conversation, ConversationMember, Message, MessageAttachment
from app.policies.access import user_access, conversation_access
from app.repositories.common import insert_once, notify
from app.services.media import unbound_media
from app.services.presenters import asset_summary


def start_conversation(db, viewer, other):
    if viewer == other:
        raise HTTPException(422, "Choose another person")
    user_access(db, other, viewer)
    pair = ":".join(sorted([viewer, other]))
    insert_once(db, Conversation, pair_key=pair)
    conv = db.scalar(select(Conversation).where(Conversation.pair_key == pair))
    for user_id in (viewer, other):
        insert_once(db, ConversationMember, conversation_id=conv.id, user_id=user_id)
    return {"id": conv.id}


def message_summary(row):
    return {
        "id": row.id,
        "sender_id": row.sender_id,
        "body": row.body,
        "created_at": row.created_at,
        "client_id": row.client_id,
        "attachments": [asset_summary(a.asset) for a in row.attachments],
    }


def send_message(db, conversation_id, viewer, data):
    members = conversation_access(db, conversation_id, viewer)
    previous = db.scalar(
        select(Message).where(
            Message.conversation_id == conversation_id,
            Message.sender_id == viewer,
            Message.client_id == str(data.client_id),
        )
    )
    if previous:
        return message_summary(previous)
    assets = [unbound_media(db, id_, viewer) for id_ in data.media_ids]
    if len(set(data.media_ids)) != len(data.media_ids):
        raise HTTPException(422, "Duplicate attachments")
    # Serialize retry-sensitive sends on the conversation; recheck after obtaining its lock.
    db.scalar(select(Conversation.id).where(Conversation.id == conversation_id).with_for_update())
    previous = db.scalar(
        select(Message).where(
            Message.conversation_id == conversation_id,
            Message.sender_id == viewer,
            Message.client_id == str(data.client_id),
        )
    )
    if previous:
        return message_summary(previous)
    row = Message(
        conversation_id=conversation_id,
        sender_id=viewer,
        body=data.body,
        client_id=str(data.client_id),
        attachments=[MessageAttachment(media_id=a.id) for a in assets],
    )
    db.add(row)
    db.flush()
    for m in members:
        if m.user_id != viewer:
            notify(db, m.user_id, viewer, "message", conversation_id, key=f"message:{row.id}:{m.user_id}")
    return message_summary(row)
