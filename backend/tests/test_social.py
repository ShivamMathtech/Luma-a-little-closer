def test_post_crud_permissions(account, post):
    a, au = account()
    b, bu = account("bob")
    p = post(a)
    assert b.patch(f"/api/v1/posts/{p['id']}", json={"caption": "stolen"}).status_code == 403
    assert b.delete(f"/api/v1/posts/{p['id']}").status_code == 403
    assert a.patch(f"/api/v1/posts/{p['id']}", json={"caption": "Edited #mountains"}).status_code == 200
    assert a.get("/api/v1/hashtags/mountains/posts").json()["items"][0]["id"] == p["id"]
    assert a.delete(f"/api/v1/posts/{p['id']}").status_code == 200
    assert a.get(f"/api/v1/posts/{p['id']}").status_code == 404


def test_likes_comments_and_replies(account, post):
    a, _ = account()
    b, _ = account("bob")
    p = post(a)
    path = f"/api/v1/posts/{p['id']}"
    for _ in range(2):
        assert b.put(path + "/like").status_code == 200
    assert a.get(path).json()["likes_count"] == 1
    c = b.post(path + "/comments", json={"body": "Love it"}).json()
    r = a.post(path + "/comments", json={"body": "Thanks", "parent_id": c["id"]})
    assert r.status_code == 201
    assert a.patch(f"/api/v1/comments/{c['id']}", json={"body": "Changed"}).status_code == 403
    assert b.patch(f"/api/v1/comments/{c['id']}", json={"body": "Great!"}).status_code == 200
    assert a.put(f"/api/v1/comments/{c['id']}/like").status_code == 200
    assert a.get(path + "/comments").json()["items"][1]["likes_count"] == 1
    assert b.delete(path + "/like").status_code == 200
    assert b.delete(path + "/like").status_code == 200
    assert a.get(path).json()["likes_count"] == 0
    assert a.delete(f"/api/v1/comments/{c['id']}").status_code == 200
    assert a.get(path + "/comments").json()["items"] == []


def test_private_follow_and_media(account, post):
    a, au = account(private=True)
    b, bu = account("bob")
    p = post(a)
    assert b.get(f"/api/v1/posts/{p['id']}").status_code == 403
    assert b.get(p["media"][0]["url"]).status_code == 403
    assert b.get("/api/v1/explore").json()["items"] == []
    assert b.get("/api/v1/users/alice/followers").status_code == 403
    assert b.post(f"/api/v1/users/{au['id']}/follow").json()["status"] == "requested"
    req = a.get("/api/v1/users/me/follow-requests").json()["items"][0]
    assert a.post(f"/api/v1/users/me/follow-requests/{req['id']}/accept").status_code == 200
    assert b.get(f"/api/v1/posts/{p['id']}").status_code == 200
    assert b.get(p["media"][0]["url"]).status_code == 200
    assert b.get("/api/v1/feed").json()["items"][0]["id"] == p["id"]
    assert b.delete(f"/api/v1/users/{au['id']}/follow").status_code == 200
    assert b.get(p["media"][0]["url"]).status_code == 403


def test_follow_idempotency_and_self(account, db):
    a, au = account()
    b, bu = account("bob")
    assert a.post(f"/api/v1/users/{au['id']}/follow").status_code == 422
    for _ in range(2):
        assert a.post(f"/api/v1/users/{bu['id']}/follow").status_code == 200
    assert a.get("/api/v1/users/bob").json()["followers_count"] == 1
    assert a.get("/api/v1/users/alice/following").json()["items"][0]["id"] == bu["id"]


def test_block_and_mute(account, post):
    a, au = account()
    b, bu = account("bob")
    p = post(a)
    b.post(f"/api/v1/users/{au['id']}/follow")
    assert b.put(f"/api/v1/users/{au['id']}/mute").status_code == 200
    assert b.get("/api/v1/feed").json()["items"] == []
    assert b.get(f"/api/v1/posts/{p['id']}").status_code == 200
    assert a.put(f"/api/v1/users/{bu['id']}/block").status_code == 200
    assert b.get(f"/api/v1/posts/{p['id']}").status_code == 404
    assert b.get(p["media"][0]["url"]).status_code == 404
    assert b.get("/api/v1/search?q=alice").json()["users"] == []
    assert b.post(f"/api/v1/users/{au['id']}/follow").status_code == 404
    assert a.get("/api/v1/users/me/relationships/blocks").json()["items"][0]["id"] == bu["id"]


def test_cursor_no_duplicates_and_validation(account, post):
    a, _ = account()
    for i in range(3):
        post(a, f"Photo {i}")
    page = a.get("/api/v1/feed?limit=2").json()
    next_page = a.get("/api/v1/feed", params={"limit": 2, "cursor": page["next_cursor"]}).json()
    assert len(page["items"]) == 2 and len(next_page["items"]) == 1
    assert not {p["id"] for p in page["items"]} & {p["id"] for p in next_page["items"]}
    assert a.get("/api/v1/feed?cursor=invalid").status_code == 422
    assert a.get("/api/v1/feed?limit=1000").status_code == 422


def test_collections_ownership(account, post):
    a, _ = account()
    b, _ = account("bob")
    p = post(a)
    cid = a.post("/api/v1/collections", json={"name": "Inspiration"}).json()["id"]
    assert b.get(f"/api/v1/collections/{cid}/posts").status_code == 404
    assert a.put(f"/api/v1/collections/{cid}/posts/{p['id']}").status_code == 200
    assert len(a.get("/api/v1/saved").json()["items"]) == 1
    assert len(a.get(f"/api/v1/collections/{cid}/posts").json()["items"]) == 1
    assert a.delete(f"/api/v1/collections/{cid}/posts/{p['id']}").status_code == 200
    assert a.patch(f"/api/v1/collections/{cid}", json={"name": "New name"}).status_code == 200
    assert a.delete(f"/api/v1/collections/{cid}").status_code == 200


def test_search_private_content_and_mentions(account, post):
    a, au = account(private=True)
    b, bu = account("bob")
    post(a, "Hidden #secret @bob")
    result = b.get("/api/v1/search?q=secret").json()
    assert result["hashtags"] == []
    assert b.get("/api/v1/hashtags/secret/posts").json()["items"] == []
    assert b.get("/api/v1/search?q=alice").json()["users"][0]["id"] == au["id"]
