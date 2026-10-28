from datetime import datetime
from typing import Generic, TypeVar
from pydantic import BaseModel, ConfigDict


class Output(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserOut(Output):
    id: str
    username: str
    display_name: str
    bio: str
    website: str
    avatar_id: str | None
    is_private: bool


class MeOut(UserOut):
    email: str
    role: str
    is_verified: bool


class ProfileOut(UserOut):
    followers_count: int
    following_count: int
    posts_count: int
    is_following: bool
    follow_requested: bool


class AssetOut(Output):
    id: str
    url: str
    mime_type: str
    width: int | None
    height: int | None
    status: str
    alt_text: str = ""


class PostOut(Output):
    id: str
    author: UserOut
    caption: str
    kind: str
    created_at: datetime
    media: list[AssetOut]
    likes_count: int
    comments_count: int
    is_liked: bool
    is_saved: bool


class CommentOut(Output):
    id: str
    post_id: str
    author: UserOut
    parent_id: str | None
    body: str
    created_at: datetime
    likes_count: int
    is_liked: bool


class MessageOut(Output):
    id: str
    sender_id: str
    body: str
    created_at: datetime
    client_id: str
    attachments: list[AssetOut]


T = TypeVar("T")


class PageOut(Output, Generic[T]):
    items: list[T]
    next_cursor: str | None
