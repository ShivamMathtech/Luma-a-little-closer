# Windows PowerShell setup

## Prerequisites

- Windows 10/11, PowerShell, Python **3.12**, Node.js **24**, and Docker Desktop with Linux containers and Compose v2.24 or newer. Install from each vendor’s official website and restart the terminal after installation.
- For native-backend video uploads, install a Windows FFmpeg build linked from https://ffmpeg.org/download.html and add its `bin` directory to your user PATH. Both `ffmpeg -version` and `ffprobe -version` must work. The API Docker image includes FFmpeg.
- Use `localhost` consistently in browser URLs. Mixing `127.0.0.1` and `localhost` changes cookie origins.

Check prerequisites:

```powershell
py -3.12 --version
node --version
npm --version
docker compose version
```

## Automated path

From the extracted `social-platform` folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1 -Seed
npm run dev
```

The process-only execution-policy override does not alter machine or user policy. If organizational policy prohibits it, use the manual commands below. Do not weaken a machine-wide policy.

`-Seed` is optional. Existing `.env` files are preserved. Use `-SkipInfrastructure` only when `backend/.env` already points to running PostgreSQL and Redis services. `start.ps1` is a convenience wrapper for `npm run dev`.

## Manual path

Open PowerShell in the project root:

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
docker compose -f infrastructure/docker-compose.yml up -d --wait db redis
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock -e ".[dev]"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.db.seed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The seed is optional and should run on a fresh local dataset. It leaves an existing `shivam` demo account untouched. Set `$env:DEMO_PASSWORD` before seeding if you want a different demo password.

A second terminal in `social-platform`:

```powershell
cd frontend
npm ci
npm run dev
```

A third terminal:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.workers.run
```

If PowerShell blocks `npm.ps1`, use `npm.cmd` in place of `npm` in these commands. Using explicit `python.exe` paths avoids activation-policy issues. Alternatively, activate with `.\.venv\Scripts\Activate.ps1` and use `python`, `alembic` and `uvicorn` directly. All commands above refer to real files in this project.

## Verify

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/ready
cd backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check app tests
cd ../frontend
npm run lint
npm run typecheck
npm test
npm run build
```

The frontend opens at http://localhost:5173; API documentation is http://localhost:8000/docs. The Vite development server proxies `/api` requests to the local API. Keep `VITE_API_BASE_URL` empty for this default topology.

## Verification and password recovery

After signup or a recovery request, wait for the worker’s next tick (at most roughly 30 seconds). Read the latest local email:

```powershell
Get-ChildItem backend/var/mail/*.eml | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | Get-Content
```

Open its full link in the browser. These files contain short-lived authentication links; keep them private. Production uses SMTP instead.

## Optional API containers

After copying environment examples, you can run PostgreSQL, Redis, API, and worker together:

```powershell
docker compose -f infrastructure/docker-compose.yml --profile app up -d --build --wait
```

Run only `npm run dev` **inside `frontend`** in this configuration; the root dev script would otherwise attempt to start a second API on port 8000. View file-mode emails inside the worker container, or configure SMTP.

Stop local infrastructure without deleting data:

```powershell
docker compose -f infrastructure/docker-compose.yml --profile app down
```

Named volumes preserve the database and container media. `down -v` removes these volumes and must only be used when you deliberately want to erase the local dataset.
