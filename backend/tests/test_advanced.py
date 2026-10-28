from datetime import timedelta
from uuid import uuid4
from sqlalchemy import select
from app.models import Story, AuditLog, now


def test_media_validation_unbound_ownership(account, upload):
    a, au = account()
    b, _ = account("bob")
    asset = upload(a)
    assert b.get(asset["url"]).status_code == 404
    assert b.post("/api/v1/posts", json={"media": [{"media_id": asset["id"]}]}).status_code == 403
    assert (
        a.post("/api/v1/media", files={"file": ("fake.png", b"<script>alert(1)</script>", "image/png")}).status_code
        == 415
    )
    assert a.post("/api/v1/posts", json={"kind": "reel", "media": [{"media_id": asset["id"]}]}).status_code == 422
    assert a.patch("/api/v1/users/me", json={"avatar_id": asset["id"]}).status_code == 200
    assert b.get(asset["url"]).status_code == 200


def test_story_expiry_and_viewers(account, upload, db):
    a, au = account()
    b, bu = account("bob")
    b.post(f"/api/v1/users/{au['id']}/follow")
    asset = upload(a)
    sid = a.post("/api/v1/stories", json={"media_id": asset["id"], "caption": "Today"}).json()["id"]
    assert b.get("/api/v1/stories/feed").json()["items"][0]["id"] == sid
    assert b.post(f"/api/v1/stories/{sid}/view").status_code == 200
    assert b.get(f"/api/v1/stories/{sid}/viewers").status_code == 404
    assert a.get(f"/api/v1/stories/{sid}/viewers").json()["items"][0]["id"] == bu["id"]
    db.get(Story, sid).expires_at = now() - timedelta(seconds=1)
    db.commit()
    assert b.get("/api/v1/stories/feed").json()["items"] == []
    assert b.post(f"/api/v1/stories/{sid}/view").status_code == 404
    assert b.get(asset["url"]).status_code == 404


def test_messaging_membership_retry_receipts_and_attachments(account, upload):
    a, au = account()
    b, bu = account("bob")
    c, cu = account("charlie")
    cid = a.post("/api/v1/conversations", json={"user_id": bu["id"]}).json()["id"]
    assert b.post("/api/v1/conversations", json={"user_id": au["id"]}).json()["id"] == cid
    asset = upload(a)
    data = {"body": "Hello Bob", "client_id": str(uuid4()), "media_ids": [asset["id"]]}
    first = a.post(f"/api/v1/conversations/{cid}/messages", json=data)
    assert first.status_code == 201, first.text
    assert a.post(f"/api/v1/conversations/{cid}/messages", json=data).json()["id"] == first.json()["id"]
    assert c.get(f"/api/v1/conversations/{cid}/messages").status_code == 404
    assert (
        c.post(f"/api/v1/conversations/{cid}/messages", json={"body": "intrude", "client_id": str(uuid4())}).status_code
        == 404
    )
    assert c.get(asset["url"]).status_code == 404
    assert b.get(asset["url"]).status_code == 200
    assert b.get("/api/v1/conversations").json()["items"][0]["unread_count"] == 1
    assert b.post(f"/api/v1/conversations/{cid}/read").status_code == 200
    assert b.get("/api/v1/conversations").json()["items"][0]["unread_count"] == 0
    b.put(f"/api/v1/users/{au['id']}/block")
    assert a.get(f"/api/v1/conversations/{cid}/messages").status_code == 404
    assert b.get("/api/v1/conversations").json()["items"] == []


def test_notifications_isolation_and_dedupe(account, post):
    a, _ = account()
    b, _ = account("bob")
    p = post(a)
    for _ in range(2):
        b.put(f"/api/v1/posts/{p['id']}/like")
    result = a.get("/api/v1/notifications").json()
    assert result["unread_count"] == 1 and len(result["items"]) == 1
    nid = result["items"][0]["id"]
    assert b.patch(f"/api/v1/notifications/{nid}").status_code == 404
    assert a.post("/api/v1/notifications/read-all").status_code == 200
    assert a.get("/api/v1/notifications").json()["unread_count"] == 0
    assert a.patch(f"/api/v1/notifications/{nid}?is_read=false").status_code == 200
    assert a.get("/api/v1/notifications").json()["unread_count"] == 1


def test_admin_permissions_actions_and_audit(account, post, db):
    a, au = account()
    b, bu = account("bob")
    admin, _ = account("moderator", admin=True)
    p = post(a)
    report = b.post(
        "/api/v1/reports", json={"target_type": "post", "target_id": p["id"], "reason": "Content violates rules"}
    )
    rid = report.json()["id"]
    assert b.get("/api/v1/admin/reports").status_code == 403
    assert (
        b.post(f"/api/v1/admin/reports/{rid}/actions", json={"action": "remove", "note": "Remove it"}).status_code
        == 403
    )
    assert admin.get("/api/v1/admin/reports").json()["items"][0]["id"] == rid
    assert (
        admin.post(
            f"/api/v1/admin/reports/{rid}/actions", json={"action": "remove", "note": "Reviewed content"}
        ).status_code
        == 200
    )
    assert a.get(f"/api/v1/posts/{p['id']}").status_code == 404
    assert db.scalar(select(AuditLog).where(AuditLog.action == "remove"))
    rid = b.post(
        "/api/v1/reports", json={"target_type": "user", "target_id": au["id"], "reason": "Repeated policy violations"}
    ).json()["id"]
    assert (
        admin.post(
            f"/api/v1/admin/reports/{rid}/actions", json={"action": "suspend", "note": "Reviewed account"}
        ).status_code
        == 200
    )
    assert a.get("/api/v1/auth/me").status_code == 401


def test_health_ready_and_openapi(account):
    c, _ = account()
    assert c.get("/health").json()["status"] == "ok"
    assert c.get("/ready").status_code == 200
    spec = c.get("/openapi.json").json()
    assert "/api/v1/posts" in spec["paths"] and "/api/v1/conversations" in spec["paths"]


def test_atomic_media_claim_prevents_cross_kind_reuse(account, upload):
    client, _ = account()
    asset = upload(client)
    assert client.post("/api/v1/posts", json={"media": [{"media_id": asset["id"]}]}).status_code == 201
    assert client.post("/api/v1/stories", json={"media_id": asset["id"]}).status_code == 409
    assert client.patch("/api/v1/users/me", json={"avatar_id": asset["id"]}).status_code == 409


def test_admin_review_of_private_reported_content(account, post):
    author, au = account(private=True)
    follower, fu = account("follower")
    admin, _ = account("moderator", admin=True)
    follower.post(f"/api/v1/users/{au['id']}/follow")
    req = author.get("/api/v1/users/me/follow-requests").json()["items"][0]
    author.post(f"/api/v1/users/me/follow-requests/{req['id']}/accept")
    p = post(author)
    rid = follower.post(
        "/api/v1/reports",
        json={"target_type": "post", "target_id": p["id"], "reason": "Please review this private post"},
    ).json()["id"]
    assert follower.get(f"/api/v1/admin/reports/{rid}/content").status_code == 403
    result = admin.get(f"/api/v1/admin/reports/{rid}/content")
    assert result.status_code == 200
    url = result.json()["post"]["media"][0]["url"]
    assert follower.get(url).status_code == 403
    assert admin.get(url).status_code == 200
    assert admin.get(p["media"][0]["url"]).status_code == 403


def test_websocket_authentication_protocol_and_revocation(account):
    from starlette.websockets import WebSocketDisconnect
    import pytest

    c, _ = account()
    with pytest.raises(WebSocketDisconnect):
        with c.websocket_connect("/api/v1/ws", headers={"origin": "https://evil.example"}):
            pass
    with c.websocket_connect("/api/v1/ws", headers={"origin": "http://localhost:5173"}) as ws:
        event = ws.receive_json()
        assert event == {"type": "refresh", "notifications": 0, "messages": 0}
        ws.send_text('{"send_message":"unvalidated"}')
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
        assert exc.value.code == 4400
    c.post("/api/v1/auth/logout")
    with pytest.raises(WebSocketDisconnect):
        with c.websocket_connect("/api/v1/ws", headers={"origin": "http://localhost:5173"}):
            pass


def test_content_length_limit_and_safe_validation_errors(account):
    c, _ = account()
    response = c.post("/api/v1/media", content=b"x", headers={"content-length": "999999999"})
    assert response.status_code == 413
    response = c.post("/api/v1/auth/register", json={"password": "do-not-echo-this"})
    assert response.status_code == 422
    assert "do-not-echo-this" not in response.text


def test_s3_adapter_signs_private_access_and_uploads(monkeypatch):
    from botocore.stub import Stubber
    from app.integrations.storage import S3Storage
    from app.core.config import settings

    monkeypatch.setattr(settings, "s3_bucket", "luma-test-bucket")
    monkeypatch.setattr(settings, "aws_access_key_id", "test-access-key")
    monkeypatch.setattr(settings, "aws_secret_access_key", "test-secret-key")
    store = S3Storage()
    with Stubber(store.client) as stub:
        stub.add_response(
            "put_object",
            {"ETag": '"test"'},
            {"Bucket": "luma-test-bucket", "Key": "test.jpg", "Body": b"content", "ContentType": "image/jpeg"},
        )
        store.put("test.jpg", b"content", "image/jpeg")
        stub.assert_no_pending_responses()
    url = store.url("test.jpg")
    assert "X-Amz-Signature=" in url and "X-Amz-Expires=60" in url


def test_video_upload_content_validation(account, tmp_path):
    import subprocess
    import shutil
    import pytest

    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg is optional locally; installed in CI and the API image")
    path = tmp_path / "clip.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=64x64:d=1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-y",
            str(path),
        ],
        check=True,
    )
    c, _ = account()
    media = c.post("/api/v1/media", files={"file": ("clip.bin", path.read_bytes(), "application/octet-stream")})
    assert media.status_code == 201, media.text
    assert media.json()["mime_type"] == "video/mp4"
    reel = c.post("/api/v1/posts", json={"kind": "reel", "media": [{"media_id": media.json()["id"]}]})
    assert reel.status_code == 201
    assert c.get("/api/v1/explore?kind=reel").json()["items"][0]["id"] == reel.json()["id"]


def test_cleanup_removes_abandoned_media_but_preserves_posts(account, upload, post, db):
    from app.models import Media
    from app.workers.run import tick
    from app.integrations.storage import storage

    client, _ = account()
    published = post(client)
    abandoned = upload(client)
    for mid in (published["media"][0]["id"], abandoned["id"]):
        db.get(Media, mid).created_at = now() - timedelta(days=2)
    db.commit()
    abandoned_key = db.get(Media, abandoned["id"]).object_key
    stats = tick()
    assert stats["unused_assets_removed"] == 1
    assert client.get(published["media"][0]["url"]).status_code == 200
    assert client.get(abandoned["url"]).status_code == 404
    assert abandoned_key not in {key for key, _ in storage().keys()}
