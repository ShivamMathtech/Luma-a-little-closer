from typing import Literal
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator, model_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Register(Input):
    email: EmailStr
    username: str = Field(min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_]+$")
    display_name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError("Use at least one letter and number")
        return v


class Login(Input):
    login: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class EmailInput(Input):
    email: EmailStr


class TokenInput(Input):
    token: str = Field(min_length=20, max_length=150)


class Reset(TokenInput):
    password: str = Field(min_length=12, max_length=128)
    _strength = field_validator("password")(Register.password_strength.__func__)


class ProfileUpdate(Input):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    bio: str | None = Field(default=None, max_length=300)
    website: str | None = Field(default=None, max_length=300)
    avatar_id: UUID | None = None
    is_private: bool | None = None

    @field_validator("website")
    @classmethod
    def safe_url(cls, v):
        if v and not v.startswith(("https://", "http://")):
            raise ValueError("Website must start with https:// or http://")
        return v


class MediaInput(Input):
    media_id: UUID
    alt_text: str = Field(default="", max_length=300)


class PostInput(Input):
    caption: str = Field(default="", max_length=2200)
    media: list[MediaInput] = Field(min_length=1, max_length=10)
    kind: Literal["post", "reel"] = "post"


class CaptionInput(Input):
    caption: str = Field(max_length=2200)


class CommentInput(Input):
    body: str = Field(min_length=1, max_length=1000)
    parent_id: UUID | None = None


class BodyInput(Input):
    body: str = Field(min_length=1, max_length=1000)


class StoryInput(Input):
    media_id: UUID
    caption: str = Field(default="", max_length=300)


class ConversationInput(Input):
    user_id: UUID


class MessageInput(Input):
    body: str = Field(default="", max_length=3000)
    client_id: UUID
    media_ids: list[UUID] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def not_empty(self):
        if not self.body and not self.media_ids:
            raise ValueError("Write a message or attach a file")
        return self


class CollectionInput(Input):
    name: str = Field(min_length=1, max_length=60)


class ReportInput(Input):
    target_type: Literal["post", "comment", "user"]
    target_id: UUID
    reason: str = Field(min_length=5, max_length=1000)


class ActionInput(Input):
    action: Literal["dismiss", "remove", "suspend"]
    note: str = Field(min_length=3, max_length=1000)


class DeleteAccount(Input):
    password: str = Field(min_length=1, max_length=128)
