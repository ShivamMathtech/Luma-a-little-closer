from app.schemas.outputs import PostOut, CommentOut, PageOut
from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import select, delete, exists, or_, and_
from app.core.dependencies import DB, CurrentUser, CSRF
from app.models import Post, User, Follow, PostLike, SavedPost, Comment, CommentLike, Block, PostHashtag, CollectionItem
from app.policies.access import post_access, owner, visible_users, blocked
from app.schemas.inputs import PostInput, CaptionInput, CommentInput, BodyInput
from app.services.social import create_post, update_tags
from app.services.presenters import posts_summary, comments_summary
from app.repositories.common import paginate, insert_once, notify
from app.middleware.rate_limit import rate

router = APIRouter(tags=["Posts and feeds"])


def listing(
    db, viewer, cursor, limit, *, following=False, author=None, kind=None, tag=None, saved=False, collection=None
):
    stmt = select(Post).join(User, User.id == Post.author_id).where(visible_users(viewer, hide_muted=following))
    if following:
        stmt = stmt.where(
            or_(
                Post.author_id == viewer,
                exists().where(Follow.follower_id == viewer, Follow.following_id == Post.author_id),
            )
        )
    if author:
        stmt = stmt.where(User.username == author.lower())
    if kind:
        stmt = stmt.where(Post.kind == kind)
    if tag:
        stmt = stmt.where(exists().where(PostHashtag.post_id == Post.id, PostHashtag.tag == tag.lower()))
    if saved:
        stmt = stmt.where(exists().where(SavedPost.user_id == viewer, SavedPost.post_id == Post.id))
    if collection:
        stmt = stmt.where(exists().where(CollectionItem.collection_id == collection, CollectionItem.post_id == Post.id))
    rows, nxt = paginate(db, stmt, Post, cursor, limit)
    return {"items": posts_summary(db, rows, viewer), "next_cursor": nxt}


@router.get("/feed", response_model=PageOut[PostOut])
def feed(db: DB, user: CurrentUser, cursor: str | None = None, limit: int = Query(20, ge=1, le=50)):
    return listing(db, user.id, cursor, limit, following=True)


@router.get("/explore", response_model=PageOut[PostOut])
def explore(
    db: DB,
    user: CurrentUser,
    cursor: str | None = None,
    limit: int = Query(20, ge=1, le=50),
    author: str | None = None,
    kind: str | None = None,
):
    if kind and kind not in {"post", "reel"}:
        raise HTTPException(422, "Invalid post kind")
    return listing(db, user.id, cursor, limit, author=author, kind=kind)


@router.get("/hashtags/{tag}/posts", response_model=PageOut[PostOut])
def hashtag(tag: str, db: DB, user: CurrentUser, cursor: str | None = None, limit: int = Query(20, ge=1, le=50)):
    return listing(db, user.id, cursor, limit, tag=tag)


@router.post("/posts", status_code=201, dependencies=[CSRF], response_model=PostOut)
def new_post(data: PostInput, db: DB, user: CurrentUser, request: Request):
    rate(request, "post", 20, user.id)
    post = create_post(db, user, data)
    return posts_summary(db, [post], user.id)[0]


@router.get("/posts/{post_id}", response_model=PostOut)
def detail(post_id: str, db: DB, user: CurrentUser):
    return posts_summary(db, [post_access(db, post_id, user.id)], user.id)[0]


@router.patch("/posts/{post_id}", dependencies=[CSRF], response_model=PostOut)
def edit(post_id: str, data: CaptionInput, db: DB, user: CurrentUser):
    post = post_access(db, post_id, user.id)
    owner(post.author_id, user.id)
    post.caption = data.caption
    update_tags(db, post)
    db.flush()
    return posts_summary(db, [post], user.id)[0]


@router.delete("/posts/{post_id}", dependencies=[CSRF])
def remove(post_id: str, db: DB, user: CurrentUser):
    post = post_access(db, post_id, user.id)
    owner(post.author_id, user.id)
    db.delete(post)
    return {"ok": True}


@router.put("/posts/{post_id}/like", dependencies=[CSRF])
def like(post_id: str, db: DB, user: CurrentUser):
    post = post_access(db, post_id, user.id)
    insert_once(db, PostLike, user_id=user.id, post_id=post_id)
    notify(db, post.author_id, user.id, "like", post_id)
    return {"ok": True}


@router.delete("/posts/{post_id}/like", dependencies=[CSRF])
def unlike(post_id: str, db: DB, user: CurrentUser):
    post_access(db, post_id, user.id)
    db.execute(delete(PostLike).where(PostLike.user_id == user.id, PostLike.post_id == post_id))
    return {"ok": True}


@router.put("/posts/{post_id}/save", dependencies=[CSRF])
def save(post_id: str, db: DB, user: CurrentUser):
    post_access(db, post_id, user.id)
    insert_once(db, SavedPost, user_id=user.id, post_id=post_id)
    return {"ok": True}


@router.delete("/posts/{post_id}/save", dependencies=[CSRF])
def unsave(post_id: str, db: DB, user: CurrentUser):
    db.execute(delete(SavedPost).where(SavedPost.user_id == user.id, SavedPost.post_id == post_id))
    return {"ok": True}


@router.get("/posts/{post_id}/comments", response_model=PageOut[CommentOut])
def comments(post_id: str, db: DB, user: CurrentUser, cursor: str | None = None, limit: int = Query(20, ge=1, le=50)):
    post_access(db, post_id, user.id)
    stmt = (
        select(Comment)
        .join(User, Comment.author_id == User.id)
        .where(
            Comment.post_id == post_id,
            User.is_suspended.is_(False),
            ~exists().where(
                or_(
                    and_(Block.user_id == user.id, Block.target_id == Comment.author_id),
                    and_(Block.target_id == user.id, Block.user_id == Comment.author_id),
                )
            ),
        )
    )
    rows, nxt = paginate(db, stmt, Comment, cursor, limit)
    return {"items": comments_summary(db, rows, user.id), "next_cursor": nxt}


@router.post("/posts/{post_id}/comments", status_code=201, dependencies=[CSRF], response_model=CommentOut)
def comment(post_id: str, data: CommentInput, db: DB, user: CurrentUser, request: Request):
    rate(request, "comment", 30, user.id)
    post = post_access(db, post_id, user.id)
    parent = db.get(Comment, str(data.parent_id)) if data.parent_id else None
    if data.parent_id and (not parent or parent.post_id != post_id or blocked(db, user.id, parent.author_id)):
        raise HTTPException(422, "Reply target is not available on this post")
    row = Comment(post_id=post_id, author_id=user.id, body=data.body, parent_id=str(data.parent_id) if parent else None)
    db.add(row)
    db.flush()
    notify(db, post.author_id, user.id, "comment", post_id, key=f"comment:{row.id}:{post.author_id}")
    if parent:
        notify(db, parent.author_id, user.id, "reply", post_id, key=f"reply:{row.id}:{parent.author_id}")
    return comments_summary(db, [row], user.id)[0]


@router.patch("/comments/{comment_id}", dependencies=[CSRF])
def edit_comment(comment_id: str, data: BodyInput, db: DB, user: CurrentUser):
    row = db.get(Comment, comment_id)
    if not row:
        raise HTTPException(404, "Comment not found")
    post_access(db, row.post_id, user.id)
    owner(row.author_id, user.id)
    row.body = data.body
    return {"ok": True}


@router.delete("/comments/{comment_id}", dependencies=[CSRF])
def delete_comment(comment_id: str, db: DB, user: CurrentUser):
    row = db.get(Comment, comment_id)
    if not row:
        raise HTTPException(404, "Comment not found")
    post = post_access(db, row.post_id, user.id)
    if user.id not in {row.author_id, post.author_id}:
        raise HTTPException(403, "Cannot delete this comment")
    db.delete(row)
    return {"ok": True}


@router.put("/comments/{comment_id}/like", dependencies=[CSRF])
def like_comment(comment_id: str, db: DB, user: CurrentUser):
    row = db.get(Comment, comment_id)
    if not row or blocked(db, user.id, row.author_id):
        raise HTTPException(404, "Comment not found")
    post_access(db, row.post_id, user.id)
    insert_once(db, CommentLike, comment_id=comment_id, user_id=user.id)
    return {"ok": True}


@router.delete("/comments/{comment_id}/like", dependencies=[CSRF])
def unlike_comment(comment_id: str, db: DB, user: CurrentUser):
    db.execute(delete(CommentLike).where(CommentLike.comment_id == comment_id, CommentLike.user_id == user.id))
    return {"ok": True}
