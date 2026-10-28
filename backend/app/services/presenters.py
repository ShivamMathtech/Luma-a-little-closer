from sqlalchemy import select, func
from app.models import PostLike, Comment, SavedPost, Follow, FollowRequest, Post, CommentLike


def user_summary(user):
    p = user.profile
    return {
        "id": user.id,
        "username": user.username,
        "display_name": p.display_name,
        "bio": p.bio,
        "website": p.website,
        "avatar_id": p.avatar_id,
        "is_private": user.is_private,
    }


def self_summary(user):
    return {**user_summary(user), "email": user.email, "role": user.role, "is_verified": user.is_verified}


def profile_summary(db, user, viewer):
    return {
        **user_summary(user),
        "followers_count": db.scalar(select(func.count()).select_from(Follow).where(Follow.following_id == user.id)),
        "following_count": db.scalar(select(func.count()).select_from(Follow).where(Follow.follower_id == user.id)),
        "posts_count": db.scalar(select(func.count()).select_from(Post).where(Post.author_id == user.id)),
        "is_following": db.get(Follow, (viewer, user.id)) is not None,
        "follow_requested": db.scalar(
            select(FollowRequest.id).where(FollowRequest.follower_id == viewer, FollowRequest.following_id == user.id)
        )
        is not None,
    }


def asset_summary(a, alt=""):
    return {
        "id": a.id,
        "url": f"/api/v1/media/{a.id}",
        "mime_type": a.mime_type,
        "width": a.width,
        "height": a.height,
        "status": a.status,
        "alt_text": alt,
    }


def posts_summary(db, posts, viewer):
    ids = [p.id for p in posts]
    if not ids:
        return []
    likes = dict(
        db.execute(
            select(PostLike.post_id, func.count()).where(PostLike.post_id.in_(ids)).group_by(PostLike.post_id)
        ).all()
    )
    comments = dict(
        db.execute(
            select(Comment.post_id, func.count()).where(Comment.post_id.in_(ids)).group_by(Comment.post_id)
        ).all()
    )
    liked = set(db.scalars(select(PostLike.post_id).where(PostLike.post_id.in_(ids), PostLike.user_id == viewer)))
    saved = set(db.scalars(select(SavedPost.post_id).where(SavedPost.post_id.in_(ids), SavedPost.user_id == viewer)))
    return [
        {
            "id": p.id,
            "author": user_summary(p.author),
            "caption": p.caption,
            "kind": p.kind,
            "created_at": p.created_at,
            "media": [asset_summary(m.asset, m.alt_text) for m in p.media],
            "likes_count": likes.get(p.id, 0),
            "comments_count": comments.get(p.id, 0),
            "is_liked": p.id in liked,
            "is_saved": p.id in saved,
        }
        for p in posts
    ]


def comments_summary(db, rows, viewer):
    ids = [r.id for r in rows]
    counts = dict(
        db.execute(
            select(CommentLike.comment_id, func.count())
            .where(CommentLike.comment_id.in_(ids))
            .group_by(CommentLike.comment_id)
        ).all()
    )
    liked = set(
        db.scalars(select(CommentLike.comment_id).where(CommentLike.comment_id.in_(ids), CommentLike.user_id == viewer))
    )
    return [
        {
            "id": r.id,
            "post_id": r.post_id,
            "author": user_summary(r.author),
            "parent_id": r.parent_id,
            "body": r.body,
            "created_at": r.created_at,
            "likes_count": counts.get(r.id, 0),
            "is_liked": r.id in liked,
        }
        for r in rows
    ]
