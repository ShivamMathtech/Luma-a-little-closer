import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.core.config import settings
from app.core.dependencies import DB, Admin
from app.middleware.observability import RequestMiddleware, metrics
from app.middleware.rate_limit import limiter
from app.api.v1 import auth, users, posts, discovery, media, stories, notifications, messaging, moderation, realtime

logging.basicConfig(level=settings.log_level, format="%(message)s")
app = FastAPI(
    title="Luma API",
    version="1.0.0",
    description="Original social platform. Cookie authentication; obtain /auth/csrf before mutations.",
)
app.add_middleware(RequestMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
    expose_headers=["X-Request-ID"],
)
for router in (auth, users, posts, discovery, media, stories, notifications, messaging, moderation, realtime):
    app.include_router(router.router, prefix="/api/v1")


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc):
    return JSONResponse(
        {
            "error": {"code": str(exc.status_code), "message": str(exc.detail)},
            "request_id": getattr(request.state, "request_id", None),
        },
        status_code=exc.status_code,
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc):
    details = [{"field": ".".join(map(str, e["loc"])), "message": e["msg"]} for e in exc.errors()]
    return JSONResponse(
        {"error": {"code": "validation", "message": "Check the submitted fields", "details": details}}, status_code=422
    )


@app.exception_handler(IntegrityError)
async def conflict(request: Request, exc):
    return JSONResponse(
        {
            "error": {
                "code": "conflict",
                "message": "The operation conflicts with an existing record; refresh and try again",
            }
        },
        status_code=409,
    )


@app.exception_handler(Exception)
async def unexpected(request: Request, exc):
    logging.getLogger("luma").error(
        "unexpected_error request_id=%s type=%s", getattr(request.state, "request_id", None), type(exc).__name__
    )
    return JSONResponse(
        {
            "error": {"code": "internal", "message": "Something went wrong. Try again or contact support."},
            "request_id": getattr(request.state, "request_id", None),
        },
        status_code=500,
    )


@app.get("/health", tags=["Operations"])
def health():
    return {"status": "ok"}


@app.get("/ready", tags=["Operations"])
def ready(db: DB):
    try:
        db.execute(text("SELECT 1"))
        db.execute(text("SELECT version_num FROM alembic_version"))
        if limiter.redis:
            limiter.redis.ping()
    except Exception:
        raise HTTPException(503, "A required dependency is unavailable")
    return {"status": "ready"}


@app.get("/api/v1/admin/metrics", tags=["Operations"])
def get_metrics(admin: Admin):
    return dict(metrics)
