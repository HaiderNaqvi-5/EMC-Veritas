## 2024-06-25 - Fix CORS Domain Suffix Hijacking
**Vulnerability:** CORS domain suffix hijacking due to unanchored regular expression in `allow_origin_regex`.
**Learning:** Starlette's `CORSMiddleware` uses `re.match` which only enforces matching at the beginning of the string. A regex like `r"https://(?:[a-z0-9-]+\.)?emc-veritas\.pages\.dev"` would match a malicious domain like `https://emc-veritas.pages.dev.malicious.com`.
**Prevention:** Always ensure CORS regex patterns are anchored with `$` at the end (e.g. `r"https://(?:[a-z0-9-]+\.)?emc-veritas\.pages\.dev$"`) when using Starlette/FastAPI.
