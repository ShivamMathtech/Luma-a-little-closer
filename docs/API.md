# API contract

Generated from the implemented FastAPI OpenAPI schema. Interactive docs: `http://localhost:8000/docs`. The adjacent `openapi.json` is machine-readable.

All protected routes use the `luma_access` HttpOnly cookie. Mutations require the signed CSRF cookie plus `X-CSRF-Token` and an exact configured `Origin`. Call `GET /api/v1/auth/csrf` before registering or logging in as well. Session credentials are never returned in JSON.

Successful objects are returned directly; collection pages use `{items, next_cursor}`. Mutations with no returned entity use `{ok: true}` or an explicit status. Errors use `{error: {code, message, details?}, request_id?}`. Cursor page sizes are bounded.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/admin/metrics` | Get Metrics |
| GET | `/api/v1/admin/reports` | Reports |
| POST | `/api/v1/admin/reports/{id_}/actions` | Moderate |
| GET | `/api/v1/admin/reports/{id_}/content` | Report Content |
| GET | `/api/v1/admin/reports/{id_}/media/{media_id}` | Review Media |
| GET | `/api/v1/auth/csrf` | Csrf |
| POST | `/api/v1/auth/forgot-password` | Forgot |
| POST | `/api/v1/auth/login` | Login |
| POST | `/api/v1/auth/logout` | Logout |
| POST | `/api/v1/auth/logout-all` | Logout All |
| GET | `/api/v1/auth/me` | Me |
| POST | `/api/v1/auth/refresh` | Refresh |
| POST | `/api/v1/auth/register` | Register |
| POST | `/api/v1/auth/resend-verification` | Resend |
| POST | `/api/v1/auth/reset-password` | Reset |
| POST | `/api/v1/auth/verify-email` | Verify |
| GET | `/api/v1/collections` | Collections |
| POST | `/api/v1/collections` | Create |
| PATCH | `/api/v1/collections/{id_}` | Rename |
| DELETE | `/api/v1/collections/{id_}` | Remove |
| GET | `/api/v1/collections/{id_}/posts` | Contents |
| PUT | `/api/v1/collections/{id_}/posts/{post_id}` | Add |
| DELETE | `/api/v1/collections/{id_}/posts/{post_id}` | Discard |
| PATCH | `/api/v1/comments/{comment_id}` | Edit Comment |
| DELETE | `/api/v1/comments/{comment_id}` | Delete Comment |
| PUT | `/api/v1/comments/{comment_id}/like` | Like Comment |
| DELETE | `/api/v1/comments/{comment_id}/like` | Unlike Comment |
| GET | `/api/v1/conversations` | Conversations |
| POST | `/api/v1/conversations` | Create |
| GET | `/api/v1/conversations/{id_}/messages` | History |
| POST | `/api/v1/conversations/{id_}/messages` | Send |
| POST | `/api/v1/conversations/{id_}/read` | Read |
| GET | `/api/v1/explore` | Explore |
| GET | `/api/v1/feed` | Feed |
| GET | `/api/v1/hashtags/{tag}/posts` | Hashtag |
| POST | `/api/v1/media` | Upload |
| GET | `/api/v1/media/{media_id}` | Download |
| GET | `/api/v1/notifications` | Notifications |
| POST | `/api/v1/notifications/read-all` | Read All |
| PATCH | `/api/v1/notifications/{id_}` | Set Read |
| POST | `/api/v1/posts` | New Post |
| GET | `/api/v1/posts/{post_id}` | Detail |
| PATCH | `/api/v1/posts/{post_id}` | Edit |
| DELETE | `/api/v1/posts/{post_id}` | Remove |
| GET | `/api/v1/posts/{post_id}/comments` | Comments |
| POST | `/api/v1/posts/{post_id}/comments` | Comment |
| PUT | `/api/v1/posts/{post_id}/like` | Like |
| DELETE | `/api/v1/posts/{post_id}/like` | Unlike |
| PUT | `/api/v1/posts/{post_id}/save` | Save |
| DELETE | `/api/v1/posts/{post_id}/save` | Unsave |
| POST | `/api/v1/reports` | Report |
| GET | `/api/v1/saved` | Saved |
| GET | `/api/v1/search` | Search |
| POST | `/api/v1/stories` | Create |
| GET | `/api/v1/stories/feed` | Feed |
| DELETE | `/api/v1/stories/{story_id}` | Remove |
| POST | `/api/v1/stories/{story_id}/view` | View |
| GET | `/api/v1/stories/{story_id}/viewers` | Viewers |
| DELETE | `/api/v1/users/me` | Delete Account |
| PATCH | `/api/v1/users/me` | Edit Me |
| GET | `/api/v1/users/me/export` | Export |
| GET | `/api/v1/users/me/follow-requests` | Requests |
| DELETE | `/api/v1/users/me/follow-requests/{request_id}` | Reject |
| POST | `/api/v1/users/me/follow-requests/{request_id}/accept` | Accept |
| GET | `/api/v1/users/me/relationships/{kind}` | Relationships |
| PUT | `/api/v1/users/{target_id}/block` | Block |
| DELETE | `/api/v1/users/{target_id}/block` | Unblock |
| POST | `/api/v1/users/{target_id}/follow` | Do Follow |
| DELETE | `/api/v1/users/{target_id}/follow` | Do Unfollow |
| PUT | `/api/v1/users/{target_id}/mute` | Mute |
| DELETE | `/api/v1/users/{target_id}/mute` | Unmute |
| GET | `/api/v1/users/{username}` | Profile |
| GET | `/api/v1/users/{username}/{direction}` | Follow List |
| GET | `/health` | Health |
| GET | `/ready` | Ready |

75 HTTP operations are exposed. Route schemas, request field constraints, and documented response models are in `openapi.json`.

## WebSocket

`WS /api/v1/ws` requires the access cookie and allowed Origin. It emits `{type: "refresh", notifications: number, messages: number}`. The only accepted client text frame is `ping`; unknown payloads close with 4400, invalid origins with 4403, and invalid/expired sessions with 4401. Sessions are rechecked each cycle. Message writes use the REST endpoint and are never accepted as arbitrary socket payloads. The shipped UI uses the documented polling fallback.

## Uploads and media

`POST /api/v1/media` takes one multipart `file` and returns its asset ID. Use that ID in post/story/profile/message mutations. A single upload can be attached once; a claim is atomic across all content kinds. Download and moderation-media routes perform access checks before local delivery or signed S3 redirects. Image processing removes metadata and normalizes size; videos are validated originals.

## Message retry contract

Provide a UUID `client_id` for each intended new message. A retry with the same conversation, sender and client ID returns the existing message; it does not create another notification or attachment. Keep that ID unchanged while retrying a lost response, and generate a new ID for a new message.

## Request examples

The frontend central client is the reference implementation for cookies, CSRF, expiry handling and uploads. From another client, retain its cookie jar, obtain `/auth/csrf`, and send `Origin` plus `X-CSRF-Token` on each mutation. Do not put cookies or raw reset links in logs.
