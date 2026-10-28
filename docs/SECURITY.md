# Security design and review checklist

This is an implemented engineering baseline with automated security tests, not a certification or a completed production penetration test.

## Identity and requests

- Passwords use pwdlib’s Argon2id implementation. Registration/reset require 12–128 characters and a letter and number. Unknown-account login checks use a dummy hash to reduce timing differences.
- Access and refresh cookies are HttpOnly, host-only, and configurable for Secure/SameSite. Database rows contain token hashes, never raw session tokens. Refresh rotation revokes the prior row and detects reuse. Password reset revokes all sessions.
- Before any mutation, the client obtains `/api/v1/auth/csrf`. A signed random token is returned in JSON and an HttpOnly cookie. The API requires the same token in `X-CSRF-Token`, checks its signature, and requires an exact allowed Origin. This also protects unauthenticated login/registration/reset requests.
- The frontend keeps its CSRF token in memory and cookies hold credentials. localStorage stores only light/dark appearance. CORS permits explicit origins and credentials, never `*`.
- Pydantic request objects reject unexpected fields, including role escalation. Public user presenters omit email, hashes, and session details. Production configuration refuses insecure cookies, non-HTTPS allowed origins, SQLite, local media storage, and missing SMTP/Redis.

## Authorization

- Post detail, feeds, hashtags, search-derived post results, comments, likes, stories, and media all apply public/private access and blocks on the server.
- Profile summaries may show a private account’s display name, bio and relationship counts; content and follower lists remain restricted.
- Both participants must be members of a conversation. Blocked or suspended peers cannot use its history, sends, or attachment URLs. Starting a private-account conversation requires approved follow access. Existing membership persists when an ordinary follow is later removed; a block closes access.
- Collections, exports, notification state, profile changes, and account deletion are scoped to the authenticated owner.
- Admin dependencies check the database role. Admin content review is a separate audited path; being an admin does not silently bypass ordinary private-post endpoints. Only media associated with the reviewed report can use the moderation media endpoint.

## Media and rendering

- JPEG/PNG/WebP files are decoded and re-encoded to JPEG, orientation normalized and metadata discarded; dimensions are capped at 20 million pixels and resized to at most 2400px per side. SVG/HTML and spoofed image payloads are rejected.
- MP4/WebM content is inspected by ffprobe, capped at 3 minutes and 4096px, and checked for supported video codecs. Browser MIME and filenames are not authoritative. Without ffprobe, video upload returns an explicit unavailable error.
- Random object names prevent path traversal. Objects are private. Local media is served through authenticated routes; S3 signed GET links expire after 60 seconds. Previously issued signed links can remain usable until that expiry following a block or deletion.
- Every upload is claimed atomically when attached, preventing cross-kind reuse races. Request body and file size limits are enforced separately.
- React renders user text without `dangerouslySetInnerHTML`. Profile website URLs accept only HTTP/HTTPS. Message bodies and captions are not executed as HTML.

## Review before public deployment

- [x] Ownership, membership, private-account, block and admin boundaries exercised by integration tests.
- [x] CSRF/origin rejection, session rotation/replay/expiry, mass assignment and throttling tested.
- [x] Response contracts filter sensitive data; safe error responses omit submitted secrets.
- [x] Database uniqueness, transactions and media claims implemented.
- [ ] Run the supplied suite against native PostgreSQL in your hosting topology, including concurrent workloads.
- [ ] Smoke-test actual SMTP, private S3 policies, Redis, cookie behavior and any proxy headers.
- [ ] Configure TLS, HSTS and a deployment-specific CSP; CSP must allow the chosen API/media origins, `blob:` previews and only required resources.
- [ ] Limit trusted reverse proxies. Do not trust arbitrary client-supplied X-Forwarded-For. Rate limiting uses the ASGI client address; configure Uvicorn proxy trust narrowly for your host.
- [ ] Run dependency/image vulnerability scans and an independent penetration review for public launch.
- [ ] Configure backups, key rotation, monitoring, incident response and operator access.

OAuth, MFA, antivirus/content-scanning services, sophisticated abuse detection and platform-scale DoS protection are not implemented. They are not represented by working-looking controls. Login/upload/search/message/recovery limits are implemented; infrastructure must still enforce TLS, connection and bandwidth limits.

Use `npm audit --omit=dev`, a current Python dependency audit tool, and container scans during release maintenance. Update exact pins and regenerate lockfiles in a reviewed change; rerun tests and builds. Security headers supplied by the API include `nosniff`, request IDs, private/no-store behavior, and a same-origin referrer policy. The frontend deployment config includes `nosniff`, referrer policy and framing denial; host-specific CSP/HSTS remain operator settings.
