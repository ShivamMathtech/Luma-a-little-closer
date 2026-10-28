"""Run PostgreSQL-compatible QA without Docker. Never use this runtime for production."""
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
PYTHON = BACKEND / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
SERVER = Path(__file__).parent / "node_modules/@electric-sql/pglite-socket/dist/scripts/server.js"

def run():
    if not SERVER.exists():
        raise SystemExit("Run npm --prefix qa/postgres ci first")
    if not PYTHON.exists():
        raise SystemExit("Install the backend virtual environment first")
    with tempfile.TemporaryDirectory(prefix="luma-pg-qa-") as directory:
        port = 55432
        log = open(Path(directory) / "server.log", "w")
        proc = subprocess.Popen(["node", str(SERVER), "-d", str(Path(directory) / "db"), "-p", str(port), "-h", "127.0.0.1", "-m", "10"], stdout=log, stderr=log)
        try:
            for _ in range(160):
                if proc.poll() is not None:
                    raise RuntimeError("PGlite exited: " + (Path(directory) / "server.log").read_text())
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                        break
                except OSError:
                    time.sleep(0.25)
            else:
                raise RuntimeError("Timed out starting PGlite")
            url = f"postgresql+psycopg://postgres@127.0.0.1:{port}/postgres"
            env = {**os.environ, "DATABASE_URL": url, "TEST_DATABASE_URL": url, "ENVIRONMENT": "test", "REDIS_URL": ""}
            commands = [[str(PYTHON), "-m", "alembic", "upgrade", "head"], [str(PYTHON), "-m", "alembic", "check"], [str(PYTHON), "-m", "pytest", "-q"], [str(PYTHON), "-m", "alembic", "downgrade", "base"], [str(PYTHON), "-m", "alembic", "upgrade", "head"]]
            for command in commands:
                subprocess.run(command, cwd=BACKEND, env=env, check=True)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill(); proc.wait()
            log.close()

if __name__ == "__main__":
    run()
