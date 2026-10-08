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

    def delete_many(self, keys: list[str]) -> None:
        """Permanently remove immutable objects that no longer have a record."""
        prefixes = sorted({key for key in keys if key})
        if not prefixes:
            return
        try:
            response = httpx.delete(
                self.base_url,
                headers={**self.headers, "Content-Type": "application/json"},
                json={"prefixes": prefixes},
                timeout=30,
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise RuntimeError("Supabase Storage deletion failed") from error

    def signed_download_url(self, key: str, filename: str, expires_in: int = 60) -> str:
        """Create a short-lived URL so the browser downloads from Storage directly."""
        try:
            response = httpx.post(
                f"{settings.supabase_url.rstrip('/')}/storage/v1/object/sign/{self.bucket}/{quote(key, safe='/')}",
                headers={**self.headers, "Content-Type": "application/json"},
                json={"expiresIn": expires_in},
                timeout=10,
            )
            response.raise_for_status()
            signed_path = response.json().get("signedURL")
            if not signed_path:
                raise RuntimeError("Supabase Storage returned no signed URL")
            signed_url = (
                signed_path
                if signed_path.startswith("http")
                else f"{settings.supabase_url.rstrip('/')}/storage/v1{signed_path}"
            )
            separator = "&" if "?" in signed_url else "?"
            return f"{signed_url}{separator}download={quote(filename)}"
        except (httpx.HTTPError, ValueError, TypeError) as error:
            raise RuntimeError("Supabase Storage signed URL creation failed") from error
