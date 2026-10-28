# Verification record

Validated on 28 October 2026 in a Linux authoring environment using Python 3.12.14 and Node.js 24.22.1. This record distinguishes executed checks from supplied configuration and deployment instructions.

## Executed checks

| Check | Result | What it establishes |
| --- | --- | --- |
| Backend `python -m pytest -q`, temporary SQLite database | **28 passed** | API behavior, access policies, persistence, security boundaries, provider adapter contracts and cleanup behavior. |
| Same backend suite through the optional PGlite PostgreSQL compatibility harness | **28 passed** | The application queries and migrations run against PostgreSQL compiled to WebAssembly. These are the same tests, not 28 additional unique cases. |
| Alembic upgrade, schema drift check, downgrade to base, upgrade to head through PGlite | **Passed**; no new upgrade operations detected | Both migration revisions apply and reverse, and model metadata matches the resulting schema. |
| Frontend `npm test` | **18 passed** in four files | Authentication boundaries, form validation, social actions, uploads and malformed API response handling. |
| Frontend `npm run lint` | **Passed** | ESLint rules pass for the delivered source. |
| Frontend `npm run build` | **Passed** | TypeScript project compilation and the Vite production bundle complete. Largest generated JavaScript chunk: 369.20 kB, 113.60 kB gzip. |
| Backend `ruff check app tests` | **Passed** | Python lint checks pass. |
| `qa/restart.py`, real Uvicorn process and HTTP requests | **Passed** | Registration, image upload and publication work; the database-backed login session, saved post and protected media survive API restart; logout then denies access. |
| Development launcher and shell setup syntax checks | **Passed** | `node --check scripts/dev.mjs` and `bash -n scripts/setup.sh` accept the scripts. This does not prove Docker or Windows execution. |
| Browser inspection | **Limited pass** | The landing page and login page rendered, and empty-login validation was inspected. No authenticated browser journey was completed. |

There are **46 unique automated tests**: 28 backend and 18 frontend. The restart check and migration exercises are additional integration checks. A test count is not a claim of complete scenario coverage or a security audit.

## Coverage highlights

Backend checks include registration and login; CSRF and Origin enforcement; access and refresh expiration, rotation and replay rejection; verification and password reset through the file mail outbox; logout everywhere; export and deletion; rate limits; validation and privilege escalation rejection; post ownership and pagination; comments, replies and likes; bookmarks and collections; private follow approval; bidirectional blocks and mutes; private search and media visibility; content validation; atomic media attachment claims; expiring stories and viewer access; conversation membership, attachments, read state and retry deduplication; notification isolation; administrator roles and audited private-report review; WebSocket authentication and message restrictions; request size limits; readiness and OpenAPI contracts; S3 SDK requests with a stub; FFmpeg-based video validation; and orphan/media cleanup.

Frontend tests exercise actual components and the central API client. The API client rejects an HTML fallback returned with HTTP 200 and application error payloads returned with an otherwise successful HTTP status, so these failures surface as errors instead of being accepted as data.

## Reproduce

Use a fresh environment following [Windows setup](WINDOWS_SETUP.md) or the README. From `backend`, with the virtual environment active:

```text
ruff check app tests
python -m pytest -q
```

From `frontend`:

```text
npm ci
npm run lint
npm test
npm run build
```

For the optional compatibility check, from the project root with the backend virtual environment active:

```text
npm --prefix qa/postgres ci
python qa/postgres/run.py
python qa/restart.py
```

The default backend suite uses a temporary SQLite database. `TEST_DATABASE_URL` may target a **disposable PostgreSQL database only**: the test fixture clears application tables. The optional harness creates and discards its own database. Never use an existing personal, staging or production account database for these tests.

Native PostgreSQL 17 checks are configured in `.github/workflows/ci.yml`, including migrations, schema drift and rollback/reapplication. That workflow has not been executed in this authoring environment.

## Not verified here

- Windows PowerShell execution, Docker Desktop/Compose startup and the native multi-container topology. Scripts and configuration are supplied, but the authoring environment could not run that topology.
- A native PostgreSQL server, multiple concurrent database backends, production load, backup restoration or failover. PGlite is a compatibility check, not evidence for those properties.
- Live SMTP delivery, live private S3 storage and a live Redis server. The S3 test uses an SDK stub; file-mode mail and the local rate-limit implementation were exercised.
- A live Vercel deployment, independent API/worker hosting, custom domains, TLS and production cookie behavior across those hosts.
- A complete authenticated browser end-to-end journey or a full mobile accessibility audit. The managed browser preview could render the frontend, but could not run the Python backend environment.
- External dependency vulnerability auditing, penetration testing, distributed tracing or external monitoring integration.

See [feature status](FEATURE_STATUS.md) for explicit scope limits and [deployment](DEPLOYMENT.md) for the required environment-specific smoke tests. The source is ready to install and evaluate; production readiness depends on completing those operational checks.

## Source archive

The deliverable includes application source, tests, migrations, lockfiles, setup scripts, infrastructure configuration and documentation. It excludes actual `.env` files, databases, uploaded media, virtual environments, dependency directories, caches and generated build output. `SOURCE_MANIFEST.sha256` lists SHA-256 checksums for the included source files, excluding the manifest itself. Install dependencies and generate environment files using the documented setup process.
