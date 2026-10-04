## 2024-05-24 - [Anchor CORS Regex]
**Vulnerability:** Starlette/FastAPI `CORSMiddleware` uses `re.match` which only checks the beginning of a string, allowing attackers to hijack domains by appending to them (e.g., `.attacker.com`).
**Learning:** In FastAPI, `allow_origin_regex` must be anchored with `$` to prevent domain suffix hijacking.
**Prevention:** Always append `$` to the end of `allow_origin_regex` values.
