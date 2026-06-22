import time
import uuid
import structlog
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = structlog.get_logger()


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(trace_id=trace_id)
        response = await call_next(request)
        response.headers["X-Trace-Id"] = trace_id
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window per-client API rate limiting (NFR 5.3 / security hardening).

    Disabled when RATE_LIMIT_PER_MINUTE <= 0. Uses Redis counters when available
    (shared across workers) and falls back to an in-process window otherwise.
    """
    def __init__(self, app):
        super().__init__(app)
        from app.core.config import get_settings
        self._limit = get_settings().RATE_LIMIT_PER_MINUTE
        self._local: dict = defaultdict(lambda: [0, 0.0])  # key -> [count, window_start]
        self._redis = None

    async def dispatch(self, request: Request, call_next):
        if self._limit <= 0:
            return await call_next(request)
        client = request.client.host if request.client else "anon"
        auth = request.headers.get("authorization", "")
        key = f"rl:{client}:{auth[:24]}"
        if not await self._allow(key):
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
        return await call_next(request)

    async def _allow(self, key: str) -> bool:
        window = int(time.time() // 60)
        wkey = f"{key}:{window}"
        try:
            redis = await self._get_redis()
            if redis is not None:
                n = await redis.incr(wkey)
                if n == 1:
                    await redis.expire(wkey, 65)
                return n <= self._limit
        except Exception:
            pass  # fall back to in-process
        count, start = self._local[key]
        now = time.time()
        if now - start >= 60:
            self._local[key] = [1, now]
            return True
        count += 1
        self._local[key][0] = count
        return count <= self._limit

    async def _get_redis(self):
        if self._redis is None:
            from app.core.config import get_settings
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(get_settings().REDIS_URL)
        return self._redis
