from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import (
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Index,
    Integer,
    JSON,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


def now():
    return datetime.now(timezone.utc)


def uid():
    return str(uuid4())


class Entity:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


def fk(table, **kw):
    return mapped_column(String(36), ForeignKey(f"{table}.id", ondelete="CASCADE"), **kw)


class User(Entity, Base):
    __tablename__ = "users"
    username: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(12), default="user")
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_suspended: Mapped[bool] = mapped_column(Boolean, default=False)
    profile: Mapped["Profile"] = relationship(cascade="all, delete-orphan", uselist=False, lazy="joined")
    __table_args__ = (CheckConstraint("role IN ('user', 'admin')", name="valid_role"),)


class Profile(Base):
    __tablename__ = "user_profiles"
    user_id: Mapped[str] = fk("users", primary_key=True)
    display_name: Mapped[str] = mapped_column(String(80), default="")
    bio: Mapped[str] = mapped_column(String(300), default="")
    website: Mapped[str] = mapped_column(String(300), default="")
    avatar_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("media_assets.id", ondelete="SET NULL"), nullable=True
    )


class Session(Entity, Base):
    __tablename__ = "user_sessions"
    user_id: Mapped[str] = fk("users", index=True)
    family_id: Mapped[str] = mapped_column(String(36), index=True)
    access_hash: Mapped[str] = mapped_column(String(64), unique=True)
    refresh_hash: Mapped[str] = mapped_column(String(64), unique=True)
    access_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class VerificationToken(Entity, Base):
    __tablename__ = "email_verification_tokens"
    user_id: Mapped[str] = fk("users", index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ResetToken(Entity, Base):
    __tablename__ = "password_reset_tokens"
    user_id: Mapped[str] = fk("users", index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Media(Entity, Base):
    __tablename__ = "media_assets"
    owner_id: Mapped[str] = fk("users", index=True)
    object_key: Mapped[str] = mapped_column(String(100), unique=True)
    mime_type: Mapped[str] = mapped_column(String(60))
    size: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="ready")
    claimed: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)


class Post(Entity, Base):
    __tablename__ = "posts"
    author_id: Mapped[str] = fk("users", index=True)
    caption: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(10), default="post")
    author: Mapped[User] = relationship(lazy="joined")
    media: Mapped[list["PostMedia"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="PostMedia.position"
    )
    __table_args__ = (
        Index("ix_posts_author_created", "author_id", "created_at", "id"),
        CheckConstraint("kind IN ('post','reel')", name="post_kind"),
    )


class PostMedia(Entity, Base):
    __tablename__ = "post_media"
    post_id: Mapped[str] = fk("posts", index=True)
    media_id: Mapped[str] = fk("media_assets", unique=True)
    position: Mapped[int] = mapped_column(Integer)
    alt_text: Mapped[str] = mapped_column(String(300), default="")
    asset: Mapped[Media] = relationship(lazy="joined")


class Comment(Entity, Base):
    __tablename__ = "comments"
    post_id: Mapped[str] = fk("posts", index=True)
    author_id: Mapped[str] = fk("users")
    parent_id: Mapped[str | None] = fk("comments", nullable=True)
    body: Mapped[str] = mapped_column(String(1000))
    author: Mapped[User] = relationship(lazy="joined")
    __table_args__ = (Index("ix_comments_post_created", "post_id", "created_at", "id"),)


class PostLike(Base):
    __tablename__ = "post_likes"
    post_id: Mapped[str] = fk("posts", primary_key=True)
    user_id: Mapped[str] = fk("users", primary_key=True)


class CommentLike(Base):
    __tablename__ = "comment_likes"
    comment_id: Mapped[str] = fk("comments", primary_key=True)
    user_id: Mapped[str] = fk("users", primary_key=True)


class Follow(Base):
    __tablename__ = "follows"
    follower_id: Mapped[str] = fk("users", primary_key=True)
    following_id: Mapped[str] = fk("users", primary_key=True, index=True)
    __table_args__ = (CheckConstraint("follower_id <> following_id", name="follow_not_self"),)


class FollowRequest(Entity, Base):
    __tablename__ = "follow_requests"
    follower_id: Mapped[str] = fk("users", index=True)
    following_id: Mapped[str] = fk("users", index=True)
    __table_args__ = (
        UniqueConstraint("follower_id", "following_id"),
        CheckConstraint("follower_id <> following_id", name="request_not_self"),
    )


class Block(Base):
    __tablename__ = "blocks"
    user_id: Mapped[str] = fk("users", primary_key=True)
    target_id: Mapped[str] = fk("users", primary_key=True, index=True)
    __table_args__ = (CheckConstraint("user_id <> target_id", name="block_not_self"),)


class Mute(Base):
    __tablename__ = "mutes"
    user_id: Mapped[str] = fk("users", primary_key=True)
    target_id: Mapped[str] = fk("users", primary_key=True)
    __table_args__ = (CheckConstraint("user_id <> target_id", name="mute_not_self"),)


class SavedPost(Entity, Base):
    __tablename__ = "saved_posts"
    user_id: Mapped[str] = fk("users", index=True)
    post_id: Mapped[str] = fk("posts", index=True)
    __table_args__ = (UniqueConstraint("user_id", "post_id"),)


class Collection(Entity, Base):
    __tablename__ = "collections"
    user_id: Mapped[str] = fk("users", index=True)
    name: Mapped[str] = mapped_column(String(60))
    __table_args__ = (UniqueConstraint("user_id", "name"),)


class CollectionItem(Base):
    __tablename__ = "collection_items"
    collection_id: Mapped[str] = fk("collections", primary_key=True)
    post_id: Mapped[str] = fk("posts", primary_key=True)


class Hashtag(Base):
    __tablename__ = "hashtags"
    tag: Mapped[str] = mapped_column(String(50), primary_key=True)


class PostHashtag(Base):
    __tablename__ = "post_hashtags"
    post_id: Mapped[str] = fk("posts", primary_key=True)
    tag: Mapped[str] = mapped_column(
        String(50), ForeignKey("hashtags.tag", ondelete="CASCADE"), primary_key=True, index=True
    )


class Story(Entity, Base):
    __tablename__ = "stories"
    author_id: Mapped[str] = fk("users", index=True)
    media_id: Mapped[str] = fk("media_assets", unique=True)
    caption: Mapped[str] = mapped_column(String(300), default="")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    author: Mapped[User] = relationship(lazy="joined")
    media: Mapped[Media] = relationship(lazy="joined")


class StoryView(Base):
    __tablename__ = "story_views"
    story_id: Mapped[str] = fk("stories", primary_key=True)
    user_id: Mapped[str] = fk("users", primary_key=True)


class Notification(Entity, Base):
    __tablename__ = "notifications"
    user_id: Mapped[str] = fk("users", index=True)
    actor_id: Mapped[str] = fk("users")
    kind: Mapped[str] = mapped_column(String(30))
    target_id: Mapped[str | None] = mapped_column(String(36))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    dedupe_key: Mapped[str] = mapped_column(String(200), unique=True)
    actor: Mapped[User] = relationship(foreign_keys=[actor_id], lazy="joined")
    __table_args__ = (Index("ix_notifications_user_created", "user_id", "created_at", "id"),)


class Conversation(Entity, Base):
    __tablename__ = "conversations"
    pair_key: Mapped[str] = mapped_column(String(80), unique=True)
    members: Mapped[list["ConversationMember"]] = relationship(cascade="all, delete-orphan", lazy="selectin")


class ConversationMember(Base):
    __tablename__ = "conversation_members"
    conversation_id: Mapped[str] = fk("conversations", primary_key=True)
    user_id: Mapped[str] = fk("users", primary_key=True, index=True)
    last_read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    user: Mapped[User] = relationship(lazy="joined")


class Message(Entity, Base):
    __tablename__ = "messages"
    conversation_id: Mapped[str] = fk("conversations", index=True)
    sender_id: Mapped[str] = fk("users")
    body: Mapped[str] = mapped_column(String(3000), default="")
    client_id: Mapped[str] = mapped_column(String(36))
    attachments: Mapped[list["MessageAttachment"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    __table_args__ = (
        UniqueConstraint("conversation_id", "sender_id", "client_id"),
        Index("ix_message_history", "conversation_id", "created_at", "id"),
    )


class MessageAttachment(Entity, Base):
    __tablename__ = "message_attachments"
    message_id: Mapped[str] = fk("messages", index=True)
    media_id: Mapped[str] = fk("media_assets", unique=True)
    asset: Mapped[Media] = relationship(lazy="joined")


class Report(Entity, Base):
    __tablename__ = "reports"
    reporter_id: Mapped[str] = fk("users")
    target_type: Mapped[str] = mapped_column(String(12))
    target_id: Mapped[str] = mapped_column(String(36))
    reason: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(16), default="open", index=True)


class ModerationAction(Entity, Base):
    __tablename__ = "moderation_actions"
    report_id: Mapped[str] = fk("reports")
    moderator_id: Mapped[str] = fk("users")
    action: Mapped[str] = mapped_column(String(30))
    note: Mapped[str] = mapped_column(String(1000))


class AuditLog(Entity, Base):
    __tablename__ = "audit_logs"
    actor_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(50))
    target_id: Mapped[str] = mapped_column(String(36))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)


class MailOutbox(Entity, Base):
    __tablename__ = "mail_outbox"
    recipient: Mapped[str] = mapped_column(String(254))
    subject: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
