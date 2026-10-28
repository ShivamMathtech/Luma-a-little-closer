# Deploy the frontend and API separately

No live service has been deployed by this package. Credentials, DNS, billing and hosting accounts must be supplied by the operator. The included configuration prepares the application for deployment; it is not evidence that external services have already been connected.

## Recommended domain arrangement

Use `https://app.example.com` for Vercel and `https://api.example.com` for the persistent API. These are illustrative domains, not deployed URLs. Configure:

```dotenv
ENVIRONMENT=production
FRONTEND_URL=https://app.example.com
ALLOWED_ORIGINS=https://app.example.com
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
STORAGE_BACKEND=s3
MAIL_BACKEND=smtp
```

Generate `SECRET_KEY` with `python -c "import secrets; print(secrets.token_urlsafe(48))"` and put it in the host’s secret manager. Never commit the result. The application uses host-only cookies on the API, `credentials: include`, exact CORS origins and signed CSRF tokens. It does not need a shared cookie Domain.

A `vercel.app` frontend and an unrelated API domain are **cross-site**. Such a topology needs `COOKIE_SAMESITE=none` plus Secure cookies, and browser third-party-cookie restrictions can still break sessions. Prefer same-site custom domains. Cross-domain browser behavior must be smoke-tested in the deployed environment; automated HTTP clients do not establish that browsers will accept the cookies.

## PostgreSQL and Redis

1. Provision managed PostgreSQL and a dedicated application database/user. Use TLS. Set `DATABASE_URL` to a SQLAlchemy psycopg URL, e.g. `postgresql+psycopg://USER:PASSWORD@HOST:5432/DB?sslmode=require`. URL-encode special characters in credentials.
2. Provision private managed Redis and set `REDIS_URL` (`rediss://...` when TLS is required). API rate limiting fails closed if configured Redis is unavailable.
3. Run `alembic upgrade head` from the backend release image as a one-off migration job before switching application traffic. Run `alembic check` during release validation.
4. Keep database backups and point-in-time recovery enabled. Verify restoration before launch.

The API uses bounded SQLAlchemy pooling and disables psycopg automatic prepared statements for transaction-pooling compatibility. Revisit pool size per process relative to your managed database’s connection limit; each process defaults to 10 base connections plus 20 overflow.

## Private object storage

1. Create a bucket dedicated to this application. Block public access and enable encryption. Use lifecycle rules for old versions and backups according to your retention policy.
2. Set `S3_BUCKET`, `S3_REGION` and optionally `S3_ENDPOINT_URL` for an S3-compatible provider. Provide an instance/task role where available, otherwise server-side `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` secrets.
3. Permit only the bucket operations required by the API and worker: object put/get/delete and list for cleanup. Do not provide credentials to the frontend.
4. Uploads pass through the API for content validation and are then written to the bucket. Direct browser-to-S3 presigned upload is not exposed. Reads use permission-checked, 60-second signed GET redirects.
5. Configure the bucket’s CORS policy for the frontend origin if your provider/browser media request requires it. Verify image display and seekable video delivery, including Range responses on the resulting signed URL.

The code includes a tested SDK adapter using botocore stubs, not a verified live bucket. Never set the bucket public to fix an authorization problem.

## Persistent API and worker

Use a provider that can run a long-lived container or Python service. Deploy `backend/Dockerfile` with `backend` as the Docker build context. It installs FFmpeg and runs as a non-root user.

Production API command:

```text
uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log
```

Adjust the port to the host’s required port in its service configuration. Put a TLS reverse proxy/load balancer in front. Configure health checks against `/ready` and liveness against `/health`. Restrict proxy trust to the provider’s documented network; do not blindly use `--forwarded-allow-ips='*'` on a publicly reachable API.

Run a separate persistent service from the same image and configuration:

```text
python -m app.workers.run
```

Set SMTP host, port, sender, credentials, and TLS according to your mail provider. Verify the sending domain and transactional email deliverability. The worker retries failed email jobs up to five ticks and clears token-bearing message bodies after delivery. Alert on exhausted jobs; SMTP is at-least-once, so a crash after send and before commit can cause a repeated email.

Production readiness requires PostgreSQL, private S3, SMTP and Redis. Local filesystem media and file-mode emails are rejected in production mode. The runtime configuration guard checks these settings; it cannot verify every external service permission or DNS record.

## Vercel frontend

1. Push this source to your Git provider and import it into Vercel.
2. Set the Vercel project **Root Directory to `frontend`**, framework **Vite**, install command `npm ci`, build command `npm run build`, and output `dist`. Use Node 24.
3. Set `VITE_API_BASE_URL=https://api.example.com` without a trailing `/api/v1`. It is a public build-time API origin, not a secret.
4. `frontend/vercel.json` supplies the SPA fallback so `/p/...`, `/u/...`, and other client routes survive refresh. Assets are emitted by Vite.
5. Add the frontend custom domain and API custom domain to their respective providers, follow their returned DNS records, then enable HTTPS. Do not invent DNS target records; use the values provided by your actual hosting account.
6. Include the exact frontend origin in `ALLOWED_ORIGINS` and `FRONTEND_URL`; rebuild the frontend after changing `VITE_API_BASE_URL`.

Do not put FastAPI or the persistent worker in the Vercel frontend project. No long-lived credentials belong in a `VITE_` variable. Do not automatically allow all preview deployment origins on an API serving production users; use isolated preview infrastructure or explicitly approved origins.

## Environment reference

| Variable | Purpose |
| --- | --- |
| `ENVIRONMENT` | `development`, `test`, or `production`; production validation gate |
| `DATABASE_URL` | PostgreSQL SQLAlchemy/psycopg connection string |
| `SECRET_KEY` | Random server-only CSRF signing secret; at least 32 characters |
| `FRONTEND_URL` | Absolute origin used in email links |
| `ALLOWED_ORIGINS` | Comma-separated exact origins; no wildcard |
| `COOKIE_SECURE`, `COOKIE_SAMESITE` | TLS cookies and site relationship |
| `ACCESS_MINUTES`, `REFRESH_DAYS` | Access and refresh lifetimes; defaults 15 / 30 |
| `STORAGE_BACKEND` | `local` for development, `s3` for production |
| `MEDIA_ROOT`, `UPLOAD_MAX_MB` | Local directory and upload cap, default 30 MB |
| `S3_BUCKET`, `S3_REGION`, `S3_ENDPOINT_URL` | Private object storage configuration |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | Optional server credentials; prefer host roles |
| `MAIL_BACKEND`, `MAIL_ROOT` | `file` development outbox delivery or `smtp` |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_TLS` | Transactional email transport; STARTTLS by default |
| `REDIS_URL` | Distributed rate-limit storage; required in production |
| `RATE_LIMIT_ENABLED` | Normally true; false only in deterministic test environments |
| `LOG_LEVEL` | Application/worker logging level |
| `VITE_API_BASE_URL` | Frontend-only, public API origin; empty for local proxy |

## Smoke test and rollback

From a configured backend environment:

```text
python ../scripts/smoke.py https://api.example.com
```

Then manually register a new test account, receive and verify an actual email, log in, upload a photo/video, follow a private account, exchange a message, and confirm a blocked account cannot read the same media. Refresh a nested frontend route. Test logout, access expiry/refresh, and a second browser session.

Keep the previous frontend deployment and backend image available. Roll back application images first when schema compatibility permits; prefer forward fixes for migrations. Back up PostgreSQL before destructive changes and use provider point-in-time restore into a new database before switching connections. Test restored media references against retained object versions.

## Primary references checked

- https://vercel.com/docs/frameworks/frontend/vite
- https://vite.dev/guide/static-deploy
- https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/ (Argon2 hashing guidance; this application uses opaque sessions)
- https://www.psycopg.org/psycopg3/docs/advanced/prepare.html
- https://docs.sqlalchemy.org/en/20/orm/queryguide/index.html
- https://ffmpeg.org/download.html
