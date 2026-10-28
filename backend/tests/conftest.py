import os
import tempfile
from pathlib import Path

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "sqlite:///" + str(Path(tempfile.mkdtemp()) / "test.db")
)
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["REDIS_URL"] = ""
os.environ["MEDIA_ROOT"] = tempfile.mkdtemp()
os.environ["MAIL_ROOT"] = tempfile.mkdtemp()
os.environ["ENVIRONMENT"] = "test"
import io
import pytest
from fastapi.testclient import TestClient
from alembic import command
from alembic.config import Config
from PIL import Image
from app.main import app
from app.db.session import engine, Base, SessionLocal
from app.models import User


@pytest.fixture(scope="session", autouse=True)
def migrated():
    command.upgrade(Config("alembic.ini"), "head")
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_database(migrated):
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
def db():
    from sqlalchemy.orm import Session

    with Session(engine.execution_options(isolation_level="AUTOCOMMIT")) as session:
        yield session


@pytest.fixture
def account():
    clients = []

    def make(name="alice", private=False, admin=False):
        client = TestClient(app)
        clients.append(client)
        client.headers["Origin"] = "http://localhost:5173"
        csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
        client.headers["X-CSRF-Token"] = csrf
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": name,
                "email": name + "@example.com",
                "display_name": name.title(),
                "password": "CorrectHorse123!",
            },
        )
        assert response.status_code == 201, response.text
        user = response.json()
        if private:
            assert client.patch("/api/v1/users/me", json={"is_private": True}).status_code == 200
        if admin:
            with SessionLocal.begin() as db:
                db.get(User, user["id"]).role = "admin"
        return client, user

    yield make
    for client in clients:
        client.close()


@pytest.fixture
def image_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (40, 30), "#e99458").save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture
def upload(image_bytes):
    def make(client):
        response = client.post("/api/v1/media", files={"file": ("photo.png", image_bytes, "image/png")})
        assert response.status_code == 201, response.text
        return response.json()

    return make


@pytest.fixture
def post(upload):
    def make(client, caption="Hello #luma"):
        asset = upload(client)
        response = client.post(
            "/api/v1/posts",
            json={"caption": caption, "media": [{"media_id": asset["id"], "alt_text": "Orange test image"}]},
        )
        assert response.status_code == 201, response.text
        return response.json()

    return make
