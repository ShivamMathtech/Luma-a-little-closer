import time
import threading
from collections import defaultdict
from fastapi import HTTPException, Request
from redis import Redis, RedisError
from app.core.config import settings
from app.core.security import digest


class Limiter:
    def __init__(self):
        self.local = defaultdict(int)
        self.lock = threading.Lock()
        self.redis = (
            Redis.from_url(settings.redis_url, socket_timeout=2, socket_connect_timeout=2)
            if settings.redis_url
            else None
        )

    def hit(self, key, limit, window=60):
        if not settings.rate_limit_enabled:
            return
        bucket = int(time.time() // window)
        key = f"luma:rate:{digest(key)}:{bucket}"
        if self.redis:
            try:
                count = self.redis.eval(
                    "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]); end; return n",
                    1,
                    key,
                    window + 1,
                )
            except RedisError:
                raise HTTPException(503, "Rate limiting service unavailable; try again")
        else:
            with self.lock:
                if len(self.local) > 10000:
                    self.local = defaultdict(int, {k: v for k, v in self.local.items() if k.endswith(f":{bucket}")})
                self.local[key] += 1
                count = self.local[key]
        if count > limit:
            raise HTTPException(429, "Too many requests; try again shortly", headers={"Retry-After": str(window)})


limiter = Limiter()


def rate(request: Request, scope: str, limit: int, identity=""):
    ip = request.client.host if request.client else "unknown"
    limiter.hit(f"{scope}:{ip}:{identity}", limit)
