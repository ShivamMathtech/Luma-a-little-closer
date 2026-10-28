import json
import logging
import time
from uuid import uuid4
from collections import Counter
from starlette.responses import JSONResponse
from app.core.config import settings

metrics = Counter()
log = logging.getLogger("luma.requests")


class RequestMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        rid, started, status, size = uuid4().hex, time.perf_counter(), 500, 0
        scope.setdefault("state", {})["request_id"] = rid
        max_size = (settings.upload_max_mb + 1) * 1024 * 1024
        headers = dict(scope["headers"])
        try:
            too_large = int(headers.get(b"content-length", b"0")) > max_size
        except ValueError:
            too_large = True
        if too_large:
            return await JSONResponse(
                {"error": {"code": "request_too_large", "message": "Request is too large"}}, status_code=413
            )(scope, receive, send)

        async def bounded_receive():
            nonlocal size
            message = await receive()
            size += len(message.get("body", b""))
            if size > max_size:
                from starlette.exceptions import HTTPException

                raise HTTPException(413, "Request is too large")
            return message

        async def tagged_send(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message["headers"].extend(
                    [
                        (b"x-request-id", rid.encode()),
                        (b"x-content-type-options", b"nosniff"),
                        (b"referrer-policy", b"same-origin"),
                        (b"cache-control", b"no-store"),
                    ]
                )
            await send(message)

        try:
            await self.app(scope, bounded_receive, tagged_send)
        finally:
            elapsed = round((time.perf_counter() - started) * 1000, 2)
            route = getattr(scope.get("route"), "path", "unmatched")
            metrics["requests_total"] += 1
            metrics["errors_total"] += int(status >= 500)
            metrics["latency_ms_sum"] += elapsed
            metrics[f"responses {scope['method']} {route} {status}"] += 1
            log.info(
                json.dumps(
                    {
                        "request_id": rid,
                        "method": scope["method"],
                        "route": route,
                        "status": status,
                        "duration_ms": elapsed,
                    }
                )
            )
