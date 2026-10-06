from urllib.parse import quote

import httpx

from app.core.settings import settings


class SupabaseStorage:
    def __init__(self) -> None:
        if not settings.supabase_service_role_key:
            raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is required for persistent Storage operations")
        self.bucket = settings.supabase_storage_bucket
        self.base_url = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{self.bucket}"
        self.headers = {
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
        }

    def upload(self, key: str, content: bytes, content_type: str) -> None:
        try:
            response = httpx.post(
                f"{self.base_url}/{quote(key, safe='/')}",
                headers={**self.headers, "Content-Type": content_type, "x-upsert": "false"},
                content=content,
                timeout=30,
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise RuntimeError("Supabase Storage upload failed") from error

    def download(self, key: str) -> bytes:
        try:
            response = httpx.get(f"{self.base_url}/{quote(key, safe='/')}", headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.content
        except httpx.HTTPError as error:
            raise RuntimeError("Supabase Storage download failed") from error


class CachedSupabaseStorage(SupabaseStorage):
    """
    A Supabase storage wrapper that caches downloaded bytes in memory.
    Useful for batch operations where identical templates, signatures, or fonts
    are requested multiple times during the same request lifecycle.
    """

    def __init__(self) -> None:
        super().__init__()
        self._cache: dict[str, bytes] = {}

    def download(self, key: str) -> bytes:
        if key not in self._cache:
            self._cache[key] = super().download(key)
        return self._cache[key]
