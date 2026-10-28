import io
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from uuid import uuid4
from PIL import Image, ImageOps, UnidentifiedImageError
from fastapi import HTTPException
from sqlalchemy import select, update
from app.models import Media, PostMedia, Story, MessageAttachment, Message, Profile
from app.policies.access import owner, post_access, user_access, conversation_access
from app.core.security import expired
from app.integrations.storage import storage

Image.MAX_IMAGE_PIXELS = 20_000_000


def validate_bytes(data):
    try:
        image = Image.open(io.BytesIO(data))
        if image.format not in {"JPEG", "PNG", "WEBP"}:
            raise HTTPException(415, "Use JPEG, PNG or WebP images")
        if image.width * image.height > 20_000_000:
            raise HTTPException(413, "Image dimensions are too large")
        image.load()
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail((2400, 2400))
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=88, optimize=True)
        return output.getvalue(), "image/jpeg", ".jpg", image.width, image.height
    except (UnidentifiedImageError, OSError):
        pass
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(413, "Image dimensions are too large")
    is_mp4 = len(data) > 12 and data[4:8] == b"ftyp"
    is_webm = data[:4] == b"\x1aE\xdf\xa3"
    if not (is_mp4 or is_webm):
        raise HTTPException(415, "Unsupported media. Use JPEG, PNG, WebP, MP4 or WebM")
    if not shutil.which("ffprobe"):
        raise HTTPException(503, "Video uploads require FFmpeg/ffprobe on the API server")
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "upload"
        path.write_bytes(data)
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                capture_output=True,
                timeout=12,
                check=True,
            )
            info = json.loads(result.stdout)
            stream = next(x for x in info["streams"] if x["codec_type"] == "video")
            if (
                stream.get("codec_name") not in {"h264", "vp8", "vp9", "av1"}
                or float(info["format"].get("duration", 0)) > 180
            ):
                raise ValueError()
            if max(stream["width"], stream["height"]) > 4096:
                raise ValueError()
        except (subprocess.SubprocessError, ValueError, KeyError, StopIteration):
            raise HTTPException(415, "Use a playable H.264/VP8/VP9/AV1 video up to 3 minutes and 4096px")
    return (
        data,
        "video/mp4" if is_mp4 else "video/webm",
        ".mp4" if is_mp4 else ".webm",
        stream["width"],
        stream["height"],
    )


def create_upload(db, user_id, data):
    payload, mime, ext, width, height = validate_bytes(data)
    key = uuid4().hex + ext
    storage().put(key, payload, mime)
    asset = Media(
        owner_id=user_id, object_key=key, mime_type=mime, size=len(payload), width=width, height=height, status="ready"
    )
    db.add(asset)
    db.flush()
    return asset


def unbound_media(db, media_id, user_id):
    media = db.get(Media, str(media_id))
    if not media:
        raise HTTPException(404, "Uploaded media not found")
    owner(media.owner_id, user_id)
    if (
        db.scalar(select(PostMedia.id).where(PostMedia.media_id == media.id))
        or db.scalar(select(Story.id).where(Story.media_id == media.id))
        or db.scalar(select(MessageAttachment.id).where(MessageAttachment.media_id == media.id))
        or db.scalar(select(Profile.user_id).where(Profile.avatar_id == media.id))
    ):
        raise HTTPException(409, "This upload is already attached")
    result = db.execute(update(Media).where(Media.id == media.id, Media.claimed.is_(False)).values(claimed=True))
    if result.rowcount != 1:
        raise HTTPException(409, "This upload is already attached or being published")
    return media


def media_access(db, media_id, viewer):
    asset = db.get(Media, media_id)
    if not asset:
        raise HTTPException(404, "Media not found")
    if asset.owner_id == viewer:
        return asset
    pm = db.scalar(select(PostMedia).where(PostMedia.media_id == media_id))
    if pm:
        post_access(db, pm.post_id, viewer)
        return asset
    story = db.scalar(select(Story).where(Story.media_id == media_id))
    if story and not expired(story.expires_at):
        user_access(db, story.author_id, viewer)
        return asset
    attachment = db.scalar(select(MessageAttachment).where(MessageAttachment.media_id == media_id))
    if attachment:
        message = db.get(Message, attachment.message_id)
        conversation_access(db, message.conversation_id, viewer)
        return asset
    avatar = db.scalar(select(Profile).where(Profile.avatar_id == media_id))
    if avatar:
        user_access(db, avatar.user_id, viewer, private=False)
        return asset
    raise HTTPException(404, "Media not found")
