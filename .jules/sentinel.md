## 2024-10-06 - Domain Suffix Hijacking via Insecure CORS Regex
**Vulnerability:** The `allow_origin_regex` pattern `r"https://(?:[a-z0-9-]+\.)?emc-veritas\.pages\.dev"` in `backend/app/main.py` did not end with `$`. Starlette's `CORSMiddleware` uses `re.match` which only enforces matching at the beginning of the string, allowing domains like `https://emc-veritas.pages.dev.attacker.com` to bypass CORS.
**Learning:** Always anchor CORS regex patterns with `$` to prevent domain suffix hijacking, especially when the framework uses `re.match` under the hood.
**Prevention:** Ensure all `allow_origin_regex` patterns are strictly anchored with `$` to enforce an exact match for the end of the domain string.
