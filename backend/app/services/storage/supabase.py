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
        response = httpx.post(
            f"{self.base_url}/{quote(key, safe='/')}",
            headers={**self.headers, "Content-Type": content_type, "x-upsert": "false"},
            content=content,
            timeout=30,
        )
        response.raise_for_status()

    def download(self, key: str) -> bytes:
        response = httpx.get(f"{self.base_url}/{quote(key, safe='/')}", headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.content
