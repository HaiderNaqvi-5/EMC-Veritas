from slowapi import Limiter
from slowapi.util import get_remote_address

# In-memory token buckets, one per worker process. Behind Render the client
# IP is resolved from X-Forwarded-For by get_remote_address. If we ever run
# multiple workers and need one shared budget, point this at Redis instead.
limiter = Limiter(key_func=get_remote_address)
