from fastapi import HTTPException
from sqlalchemy import select, or_, and_, exists
from app.models import User, Follow, Block, Mute, Post, ConversationMember


def blocked(db, a, b):
    return (
        db.scalar(
            select(Block.user_id).where(
                or_(and_(Block.user_id == a, Block.target_id == b), and_(Block.user_id == b, Block.target_id == a))
            )
        )
        is not None
    )


def visible_users(viewer, *, hide_muted=False):
    clauses = [
        User.is_suspended.is_(False),
        ~exists().where(
            or_(
                and_(Block.user_id == viewer, Block.target_id == User.id),
                and_(Block.target_id == viewer, Block.user_id == User.id),
            )
        ),
        or_(
            User.id == viewer,
            User.is_private.is_(False),
            exists().where(Follow.follower_id == viewer, Follow.following_id == User.id),
        ),
    ]
    if hide_muted:
        clauses.append(~exists().where(Mute.user_id == viewer, Mute.target_id == User.id))
    return and_(*clauses)


def user_access(db, user_id, viewer, *, private=True):
    user = db.get(User, user_id)
    if not user or user.is_suspended or blocked(db, viewer, user_id):
        raise HTTPException(404, "Account not found")
    if private and user_id != viewer and user.is_private and not db.get(Follow, (viewer, user_id)):
        raise HTTPException(403, "This account is private")
    return user


def post_access(db, post_id, viewer):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(404, "Post not found")
    user_access(db, post.author_id, viewer)
    return post


def conversation_access(db, conversation_id, viewer):
    members = list(db.scalars(select(ConversationMember).where(ConversationMember.conversation_id == conversation_id)))
    if not any(m.user_id == viewer for m in members):
        raise HTTPException(404, "Conversation not found")
    for m in members:
        if m.user_id != viewer:
            user_access(db, m.user_id, viewer, private=False)
    return members


def owner(actual, expected):
    if actual != expected:
        raise HTTPException(403, "You do not own this resource")
