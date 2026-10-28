"""Real HTTP process-restart smoke test using an isolated local SQLite database."""
import io
import os
import secrets
import subprocess
import tempfile
import time
from pathlib import Path
import httpx
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / 'backend'
PYTHON = BACKEND / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
BASE = 'http://127.0.0.1:58000'


def main():
    with tempfile.TemporaryDirectory(prefix='luma-restart-') as directory:
        folder = Path(directory)
        env = {**os.environ, 'ENVIRONMENT': 'test', 'DATABASE_URL': 'sqlite:///' + (folder / 'persist.db').as_posix(),
               'REDIS_URL': '', 'MEDIA_ROOT': str(folder / 'media'), 'MAIL_ROOT': str(folder / 'mail'),
               'ALLOWED_ORIGINS': 'http://localhost:5173', 'COOKIE_SECURE': 'false', 'COOKIE_SAMESITE': 'lax'}
        subprocess.run([str(PYTHON), '-m', 'alembic', 'upgrade', 'head'], cwd=BACKEND, env=env, check=True)
        log = open(folder / 'api.log', 'w')
        process = None
        def start():
            proc = subprocess.Popen([str(PYTHON), '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '58000', '--no-access-log'], cwd=BACKEND, env=env, stdout=log, stderr=log)
            with httpx.Client(timeout=1, trust_env=False) as probe:
                for _ in range(80):
                    if proc.poll() is not None:
                        raise RuntimeError((folder / 'api.log').read_text())
                    try:
                        if probe.get(BASE + '/ready').status_code == 200:
                            return proc
                    except httpx.TransportError:
                        pass
                    time.sleep(.1)
            proc.terminate(); proc.wait()
            raise RuntimeError('API did not become ready')
        try:
            process = start()
            with httpx.Client(base_url=BASE, headers={'Origin':'http://localhost:5173'}, timeout=15, trust_env=False) as client:
                client.headers['X-CSRF-Token'] = client.get('/api/v1/auth/csrf').json()['csrf_token']
                name = 'qa_' + secrets.token_hex(5)
                password = secrets.token_urlsafe(20) + '7a'
                response = client.post('/api/v1/auth/register', json={'username':name, 'email':name+'@example.com', 'display_name':'Persistence test', 'password':password})
                assert response.status_code == 201, response.text
                uid = response.json()['id']
                image = io.BytesIO(); Image.new('RGB',(20,20),'teal').save(image,'PNG')
                response = client.post('/api/v1/media', files={'file':('image.png',image.getvalue(),'image/png')})
                assert response.status_code == 201, response.text
                media = response.json()
                response = client.post('/api/v1/posts', json={'caption':'Still here after restart', 'media':[{'media_id':media['id'],'alt_text':'Teal test square'}]})
                assert response.status_code == 201, response.text
                post = response.json()
                print('PASS real HTTP registration, upload and publication')
                process.terminate(); process.wait(timeout=10)
                process = start()
                assert client.get('/api/v1/auth/me').json()['id'] == uid
                result = client.get('/api/v1/posts/' + post['id'])
                assert result.status_code == 200 and result.json()['caption'] == 'Still here after restart'
                assert client.get(media['url']).status_code == 200
                print('PASS database-backed session, post and protected media survive API restart')
                result = client.post('/api/v1/auth/logout')
                assert result.status_code == 200
                assert client.get('/api/v1/auth/me').status_code == 401
                print('PASS logout remains enforced over real HTTP')
        finally:
            if process and process.poll() is None:
                process.terminate(); process.wait(timeout=10)
            log.close()


if __name__ == '__main__':
    main()
