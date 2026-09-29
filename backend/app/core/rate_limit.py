from slowapi import Limiter
from starlette.requests import Request


def _client_ip(request: Request) -> str:
    # Render is the only ingress and appends the true client IP as the last
    # entry of X-Forwarded-For. slowapi's get_remote_address ignores the
    # header and returns the proxy's IP, which puts every visitor in one
    # shared bucket. The last entry cannot be spoofed past Render's edge.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


# In-memory token buckets, one per worker process. If we ever run multiple
# workers and need one shared budget, point this at Redis instead.
limiter = Limiter(key_func=_client_ip)
