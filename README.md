# Luma — a little closer

An original, working social platform with a React/TypeScript frontend and a separate FastAPI API. PostgreSQL stores accounts, sessions, posts, conversations, and relationships. Media uses protected local storage for development and a private S3-compatible bucket for production. This project does not use Instagram branding or assets.

## Start on Windows

Install Python 3.12, Node.js 24, and Docker Desktop with Docker Compose. Start Docker Desktop, extract this project, and open PowerShell in `social-platform`.

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1 -Seed
npm run dev
```

The execution-policy override affects this invocation only. The setup script creates environment files and a virtual environment, installs locked dependencies, starts PostgreSQL/Redis, applies migrations, and optionally seeds demo data.

Open **http://localhost:5173**. API: **http://localhost:8000**, interactive API docs: **http://localhost:8000/docs**, health: **http://localhost:8000/health**.

Demo account after `-Seed`: **shivam / LumaDemo2026!**. Other demo usernames are `mira`, `arjun`, and `naina`, with the same development-only password. Demo content consists of four accounts and four original generated landscape illustrations. There are no preloaded data arrays in the frontend. Never seed a production database; the command refuses production mode.

Start the independent mail/cleanup worker in a second PowerShell terminal:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.workers.run
```

Local verification and reset emails appear as `.eml` files in `backend/var/mail`. Open the link in the latest email. Delivery is a queued operation, so the worker must be running. A newly registered user can use the application before verification; verified email status is tracked and displayed, not used as a posting prerequisite in this release.

For full manual steps and video support, see [Windows setup](docs/WINDOWS_SETUP.md). On Linux/macOS, install the same prerequisites and run `bash scripts/setup.sh --seed`, then `npm run dev` and the worker separately. Linux/macOS setup scripts have not been exercised against a Docker daemon in the authoring environment.

## Implemented

- Registration, login/logout, verification, password recovery, short-lived access cookies, rotating refresh sessions, reuse detection, and logout everywhere.
- Profile editing, photo avatars, public/private accounts, follow requests, follower lists, blocks, and mutes.
- Multiple-photo posts, validated MP4/WebM uploads, captions, alt text, editing/deletion, likes, threaded comments, comment likes, saved posts, and collections.
- Chronological following/discovery feeds, cursor pagination, user and hashtag search, and protected media delivery.
- Expiring stories, view tracking, owner-only viewer lists, and video/reel playback.
- One-to-one messaging, attachments, read timestamps, unread counts, cursor history, and retry-safe message IDs. The UI uses polling; a secured WebSocket invalidation endpoint is also provided.
- Notifications, mention notifications on post captions, follow requests, mark-read/unread/all-read, and notification deduplication.
- Reporting and an admin queue with private-content review, content removal, account suspension, and audit records.
- Account JSON export and password-confirmed deletion; orphaned media cleanup.
- Responsive layouts, keyboard focus, native modal dialogs, light/dark appearance, and loading/error/empty states.

## Commands

Run frontend commands from `frontend`:

```text
npm ci
npm run dev
npm run lint
npm run typecheck
npm test
npm run build
```

Run backend commands from `backend` using the activated virtual environment:

```text
python -m pip install -r requirements-dev.lock -e ".[dev]"
alembic upgrade head
alembic check
python -m app.db.seed
python -m app.workers.run
ruff check app tests
python -m pytest -q
```

`uv.lock` is the canonical Python resolution. The exported `requirements.lock` and `requirements-dev.lock` support ordinary pip. Direct package versions are exact in both application manifests; npm has `package-lock.json`. Python 3.12 and Node 24 were used for validation. CSS is a custom token-based stylesheet, an intentional alternative to Tailwind.

Tests default to a new temporary SQLite database. To run the same suite on a **disposable PostgreSQL database**, set `TEST_DATABASE_URL`. Tests clear application tables: never point that setting at a real account database. PostgreSQL CI is configured in `.github/workflows/ci.yml`.

Give an existing local account admin access with an operator command, not a frontend role field:

```text
python -m app.db.admin shivam
```

Use `--revoke` to remove the role. Moderation becomes available after refreshing the session’s account query.

## Project map

| Folder | Responsibility |
| --- | --- |
| `frontend/src/app` | Routes, authentication boundary, navigation |
| `frontend/src/features` | Feature pages |
| `frontend/src/components` | Shared UI, post/media/comments/story components |
| `frontend/src/lib` | Central API, CSRF, refresh, uploads, query invalidation |
| `backend/app/api/v1` | Versioned HTTP and WebSocket endpoints |
| `backend/app/services`, `policies`, `repositories` | Application behavior, access rules, atomic inserts/pagination |
| `backend/app/models`, `schemas`, `db` | Relational models, validated contracts, DB setup and explicit seeds |
| `backend/app/integrations`, `workers` | Storage adapters, durable mail outbox and scheduled cleanup |
| `backend/alembic` | Reproducible schema migrations |
| `infrastructure` | Persistent local PostgreSQL/Redis and optional API/worker containers |
| `qa/postgres` | Optional reproducible PGlite compatibility check; not production infrastructure |
| `docs` | Architecture, API, database, security, setup, deployment, operations and verification |

## Deployment and current limits

The frontend is prepared for Vercel; the API and worker run on a separate persistent host. No deployment has been published. Configure PostgreSQL, Redis, SMTP and private object storage before setting `ENVIRONMENT=production`; configuration validation rejects local production storage and insecure cookies.

See [deployment](docs/DEPLOYMENT.md), [feature status](docs/FEATURE_STATUS.md), and [verified results](docs/VERIFICATION.md). Actual SMTP/S3/Redis service integrations and a Docker-backed production topology require environment-specific smoke tests. Video uploads are validated originals, not transcoded renditions. OAuth, ML recommendations, adaptive streaming, external error monitoring, and push notifications are not implemented or advertised in the UI.
