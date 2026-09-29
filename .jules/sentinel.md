## 2024-05-18 - CORS Regex Missing Anchors
**Vulnerability:** The `allow_origin_regex` for CORS configuration in FastAPI (`backend/app/main.py`) lacked string boundary anchors (`^` and `$`).
**Learning:** Python's `re.match` (used internally by Starlette/FastAPI's CORSMiddleware) matches the beginning of the string by default, but doesn't require matching to the end of the string. A regex like `r"https://emc-veritas\.pages\.dev"` would incorrectly allow an attacker origin like `https://emc-veritas.pages.dev.attacker.com`.
**Prevention:** Always use explicit boundary anchors (`^` and `$`) when writing regular expressions for origin matching in CORS configuration.
