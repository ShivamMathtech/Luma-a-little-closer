# Database

All entity identifiers are random UUID strings. Timestamps are created in UTC and use timezone-aware PostgreSQL columns. Composite primary keys and unique constraints prevent duplicate relationships and engagement. Foreign keys cascade dependent content; privileged audit actor references use `SET NULL` so audit records can survive account deletion.

| Tables | Relationships and purpose |
| --- | --- |
| `users`, `user_profiles` | Unique normalized email/username; one profile per user; avatar FK points to an owned media asset. Roles are restricted to `user` and `admin`. |
| `user_sessions` | Hashed access/refresh values, expiry, revoked state, and rotation family. Old revoked refresh rows remain until expiry to detect replay. |
| `email_verification_tokens`, `password_reset_tokens` | One-use token hashes and expiry; consumed under row locks. |
| `media_assets`, `post_media`, `posts` | Binary-free metadata, generated storage key, validated dimensions/status, atomic attachment claim; ordered media, captions and post/reel kind. |
| `comments`, `comment_likes`, `post_likes` | Post comments, cascading reply tree, and unique per-user likes. Replies must belong to the same visible post. |
| `follows`, `follow_requests` | Approved edges versus pending private-account requests. Check constraints reject self-follows. |
| `stories`, `story_views` | Absolute 24-hour expiry and unique viewer edges; expired stories excluded on reads before worker deletion. |
| `saved_posts`, `collections`, `collection_items` | Owner-only saved items and named collections. Collection entries are unique. |
| `hashtags`, `post_hashtags` | Normalized caption hashtags and indexed post associations. |
| `notifications` | Recipient, actor, event type, target, read state, and unique retry-deduplication key. |
| `conversations`, `conversation_members` | Unique sorted one-to-one pair, membership and last-read timestamp. |
| `messages`, `message_attachments` | Member-authored text, unique client retry IDs and protected attachment references. |
| `blocks`, `mutes` | Directional block/mute choices; blocks apply bidirectionally to access. |
| `reports`, `moderation_actions`, `audit_logs` | Polymorphic reported targets, resolution, moderator action and privileged access/action trail. |
| `mail_outbox` | Durable email jobs, retry attempts, completion time; delivery removes the stored token-bearing message body. |

`Post.kind = 'reel'` is the video-post representation, so a separate reels table would duplicate the same engagement model. Notification/report targets are polymorphic IDs rather than impossible cross-table foreign keys. Deleted targets return not-found or a clear already-removed state. No media binaries are stored in ordinary database rows.

## Migrations

From `backend`:

```text
alembic upgrade head
alembic current
alembic check
```

`3ff31791c013` creates the initial schema. `a892be9c1041` adds atomic media claims, backfills existing attachments, and adds the profile-avatar FK. No application startup uses `create_all` in production. The optional local API container runs migrations before its single API process; production deploys should use a dedicated one-off migration job.

For a schema change, edit the models and generate a migration against a development database:

```text
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
alembic check
```

Review generated SQL and deletion behavior before production. A rollback should normally restore the prior image with a backward-compatible schema; destructive `alembic downgrade` is only appropriate after backup and review.

## Indexes and pagination

Posts have `(author_id, created_at, id)`, messages `(conversation_id, created_at, id)`, comments `(post_id, created_at, id)` and notifications `(user_id, created_at, id)` indexes. Unique usernames are indexed; following targets, hashtag joins, story expiry, and membership lookups also have indexes. Global timestamp indexes support small chronological discovery feeds; benchmark compound global ordering indexes and prefix-search indexes on real production volumes before scaling.

Tuple cursors break equal-timestamp ties with the UUID. A deleted last item does not invalidate its cursor. Newer inserts are obtained by refreshing the first page; traversal does not repeat already-returned rows because page boundaries use a strict comparison.

## Retention

Deleting an account revokes access immediately by removing its sessions and cascades authored data and relationships. Unreferenced media rows are collected after 24 hours, while storage objects without database rows are swept with a 24-hour grace period. The object bucket must be dedicated to Luma; the sweeper only recognizes generated object names. S3 versioning and backups have separate retention and need their own lifecycle policies. See OPERATIONS.md.
