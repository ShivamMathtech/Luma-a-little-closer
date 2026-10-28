# Troubleshooting

| Symptom | Check and remedy |
| --- | --- |
| PostgreSQL connection refused | Start Docker Desktop and `docker compose -f infrastructure/docker-compose.yml up -d --wait db redis`. Check `docker compose ... ps` and the configured database port. |
| `relation ... does not exist` / readiness fails | Run `alembic upgrade head` against the same database used by the API. |
| Port 8000 already in use | Stop the old API. Use either the root dev script or the optional API container, not both. |
| Empty feed after signup | Follow accounts through Explore, or publish a post. Demo rows exist only after the documented seed command. |
| Login succeeds but the next request is unauthenticated | Use `localhost` consistently locally. In production inspect Secure/SameSite/domain/CORS settings and browser third-party-cookie behavior. Prefer same-site custom domains. |
| 403 CSRF/origin | Add the exact browser origin to `ALLOWED_ORIGINS`, including scheme/port. Do not add `*`. Clients must send the cookie plus `X-CSRF-Token` from `/auth/csrf`. Restart the API after environment changes. |
| Verification/reset email is missing | Start the worker. In local file mode, inspect `backend/var/mail`; in production inspect SMTP configuration and job attempts. The API queues mail; it does not synchronously deliver it. |
| Verification/reset link expired | Request a new link. Verification links last 24 hours; reset links last one hour. Tokens are one-use. |
| Media upload says unavailable | For video, install FFmpeg/ffprobe on PATH or use the API container. For S3, verify credentials, endpoint, region, and bucket permissions. |
| Unsupported image/video | Use JPEG/PNG/WebP or a browser-playable H.264 MP4 / supported WebM video. Maximum file size defaults to 30 MB, video duration 3 minutes, video dimension 4096px. |
| Upload conflict | An upload can be attached only once. After losing a publish response, inspect your profile before retrying with new uploads. |
| Private or blocked content returns 403/404 | This is expected backend authorization. Follow approval is required; blocked/suspended resources are hidden. |
| Redis failure / 503 | Start Redis or repair its URL. Shared rate limiting fails closed in configured environments. Leave Redis empty only for one-process local development. |
| Native PowerShell script restrictions | Use explicit `.venv/Scripts/python.exe` commands. Do not change machine-wide execution policy. |
| Frontend deep link 404 after Vercel deploy | Set root directory to `frontend`, output to `dist`, and retain its `vercel.json` SPA fallback. |
| Frontend cannot reach API in production | Set and rebuild `VITE_API_BASE_URL` to the HTTPS API origin without `/api/v1`; configure API CORS for the frontend origin. |
| Demo seed does nothing | It detects an existing `shivam` account and safely leaves the dataset alone. Use a fresh disposable development database for a new seed. |
| Refresh reuse invalidates a session | Reusing an old refresh cookie intentionally revokes its family. Sign in again; do not retry the old refresh value. |

Useful commands (project root, adjust interpreter for your OS):

```text
docker compose -f infrastructure/docker-compose.yml ps
docker compose -f infrastructure/docker-compose.yml logs db redis
npm --prefix frontend run build
```

From `backend`: `alembic current`, `alembic check`, `python -m pytest -q`, and `python -m app.workers.run --once`.
