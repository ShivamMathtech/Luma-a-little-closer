# Implemented features and external dependencies

| Area | Shipped behavior | Remaining scope / verification boundary |
| --- | --- | --- |
| Identity | Real accounts, Argon2, verified-email state, recovery, access/refresh cookies, rotation/revocation, deletion | OAuth/MFA not implemented; verification is informational, not a posting gate. |
| Social graph | Public/private profiles, requests, follow lists, block/mute enforcement | No follower recommendation model. |
| Posts | Multi-image/video uploads, captions/alt text, edits/deletes, likes/comments/replies/comment likes, sharing | No rich-text editor or arbitrary HTML. |
| Discovery | Chronological feeds, account/hashtag search, cursors | No ML ranking or full-text search engine. |
| Saved | Bookmarks and private named collections with add/remove/rename/delete | Management lists remain small non-paginated lists. |
| Stories | 24-hour expiry, view state/count, owner viewer list, deletion | No camera capture, stickers, or music library. |
| Reels | Validated original video uploads, playback and normal post engagement | No transcoding, adaptive renditions, view analytics, or video-processing worker. Status `ready` means a validated original is available. |
| Messages | Persistent one-to-one conversations, attachments, timestamps, read state, unread counts, history cursors, client-ID retry dedupe | UI polling is the default. WebSocket invalidation endpoint is tested but not wired into the UI; no typing indicators or group chats. |
| Notifications | Follows/requests/approval, post likes/comments/replies, post-caption mentions and messages; deduplication and read state | No browser/mobile push, email digests, or comment-body mention notifications. |
| Moderation | Reports, role-protected queue, audited private-content review, remove/suspend/dismiss | No automated content classifier or appeal system. |
| Storage | Protected local files; private S3 adapter with signed GET; content validation and orphan cleanup | Live S3 credentials/bucket testing required. Uploads use the API, not direct signed browser uploads. |
| Mail | Durable outbox, file-mode delivery, SMTP implementation and bounded retries | Live SMTP delivery/domain configuration required. |
| Redis | Shared production rate-limit adapter, fail-closed behavior | Live Redis service integration not exercised in this authoring environment. |
| Operations | Request IDs/logs, health/readiness, basic admin metrics, worker and cleanup, CI and Docker configuration | External monitoring/tracing, backups and restore drills must be configured by the operator. |
| Deployment | Vercel SPA config, backend image, PostgreSQL/Redis Compose, Windows scripts and guides | No live hosting deployment, native Docker runtime, or Windows execution was performed here. |

See VERIFICATION.md for the exact tests executed. Mocked provider tests are not claimed as live provider integration. PGlite’s PostgreSQL compatibility is not claimed as proof of native PostgreSQL concurrency or production performance.
