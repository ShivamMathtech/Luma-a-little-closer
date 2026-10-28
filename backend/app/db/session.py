from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings


class Base(DeclarativeBase):
    pass


kwargs = {"pool_pre_ping": True}
if settings.database_url.startswith("sqlite"):
    kwargs["connect_args"] = {"check_same_thread": False}
else:
    kwargs.update(pool_size=10, max_overflow=20, pool_timeout=15, connect_args={"prepare_threshold": None})
engine = create_engine(settings.database_url, **kwargs)
if engine.dialect.name == "sqlite":

    @event.listens_for(engine, "connect")
    def sqlite_foreign_keys(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")


SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_db():
    with SessionLocal() as db:
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
