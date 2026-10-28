"""Explicit, repeatable local demo seed. Refuses production."""

import io
import os
from PIL import Image, ImageDraw
from sqlalchemy import select
from app.core.config import settings
from app.core.security import password_hasher
from app.db.session import SessionLocal
from app.models import User, Profile, Follow
from app.schemas.inputs import PostInput, MediaInput
from app.services.media import create_upload
from app.services.social import create_post
from app.repositories.common import insert_once

DEMO_USERS = [
    (
        "shivam",
        "Shivam Singh",
        "Finding the extraordinary in the everyday. Code, coffee & a little mountain air.",
        "#bd704d",
    ),
    ("mira", "Mira Kapoor", "Slow mornings and small adventures. Based somewhere near the mountains.", "#819982"),
    ("arjun", "Arjun Rao", "Designing things. Taking the long way home.", "#c3a26b"),
    ("naina", "Naina Sharma", "A notebook, a camera, and a curious mind.", "#b58077"),
]


def artwork(index, avatar=False):
    # Original procedural illustrations, generated only by this explicit seed.
    w, h = (160, 160) if avatar else (1000, 860)
    palettes = [
        ("#d7d8c0", "#f1dfb3", "#8c9d82", "#526c5d"),
        ("#ebd8c1", "#fcf0cb", "#cb9574", "#9a5d44"),
        ("#cddbd6", "#f8edc8", "#8babb0", "#526f70"),
        ("#e5d9cb", "#f6e8c3", "#b99d86", "#786b60"),
    ]
    sky, sun, far, near = palettes[index % len(palettes)]
    im = Image.new("RGB", (w, h), sky)
    d = ImageDraw.Draw(im)
    d.ellipse((w * 0.60, h * 0.10, w * 0.79, h * 0.32), fill=sun)
    d.polygon(
        [(0, h * 0.60), (w * 0.25, h * 0.28), (w * 0.5, h * 0.57), (w * 0.72, h * 0.35), (w, h * 0.52), (w, h), (0, h)],
        fill=far,
    )
    d.polygon(
        [(0, h * 0.75), (w * 0.18, h * 0.66), (w * 0.45, h * 0.82), (w * 0.7, h * 0.57), (w, h * 0.70), (w, h), (0, h)],
        fill=near,
    )
    if not avatar:
        d.line(
            [(w * 0.40, h), (w * 0.50, h * 0.86), (w * 0.62, h * 0.80), (w * 0.62, h * 0.74), (w * 0.70, h * 0.68)],
            fill=sun,
            width=7,
        )
        for x, y in [(100, 670), (160, 700), (820, 620), (890, 680)]:
            d.polygon([(x, y - 60), (x - 18, y), (x + 18, y)], fill="#344b3e")
            d.line([(x, y), (x, y + 20)], fill="#344b3e", width=4)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=92)
    return buf.getvalue()


def main():
    if settings.environment == "production":
        raise SystemExit("Demo seed is disabled in production")
    password = os.getenv("DEMO_PASSWORD", "LumaDemo2026!")
    with SessionLocal.begin() as db:
        if db.scalar(select(User.id).where(User.username == "shivam")):
            print("Demo dataset already exists; nothing changed.")
            return
        users = []
        for i, (username, name, bio, color) in enumerate(DEMO_USERS):
            user = User(
                username=username,
                email=f"{username}@example.com",
                password_hash=password_hasher.hash(password),
                is_verified=True,
                profile=Profile(display_name=name, bio=bio),
            )
            db.add(user)
            db.flush()
            avatar = create_upload(db, user.id, artwork(i, avatar=True))
            avatar.claimed = True
            user.profile.avatar_id = avatar.id
            users.append(user)
        captions = [
            "Took the longer trail. Found the quieter view. Some days, that’s everything. #mountains #slowdays",
            "A little pause between the busy parts. Keeping this kind of quiet close. #everyday #perspective",
            "The world has a way of reminding you to look up. #nature #weekend",
            "No big plans. Just good light and a little curiosity. #explore #littlemoments",
        ]
        for i, user in enumerate(users[1:] + users[:1]):
            asset = create_upload(db, user.id, artwork(i))
            create_post(
                db,
                user,
                PostInput(
                    caption=captions[i],
                    media=[
                        MediaInput(
                            media_id=asset.id,
                            alt_text="Original illustration of a sunlit mountain landscape and a winding trail",
                        )
                    ],
                ),
            )
        for user in users[1:]:
            insert_once(db, Follow, follower_id=users[0].id, following_id=user.id)
        print(
            "Seeded 4 demo accounts and 4 original illustrated posts. Username: shivam. See README for the development-only password."
        )


if __name__ == "__main__":
    main()
