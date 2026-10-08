from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import ClassVar
from urllib.parse import quote

import httpx

from app.core.settings import settings


class SupabaseStorage:
    # Storage keys are immutable UUID paths (uploads use x-upsert=false), so a
    # small process-local cache is safe and removes repeated network/TLS work
    # from previews. The bound prevents large PDFs from growing memory without
    # limit on the hosted worker.
    _download_cache: ClassVar[OrderedDict[tuple[str, str], bytes]] = OrderedDict()
    _cache_lock: ClassVar[Lock] = Lock()
    _cache_limit: ClassVar[int] = 16

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
            self._cache_put(key, content)
        except httpx.HTTPError as error:
            raise RuntimeError("Supabase Storage upload failed") from error

    def download(self, key: str) -> bytes:
        cache_key = (self.bucket, key)
        with self._cache_lock:
            cached = self._download_cache.get(cache_key)
            if cached is not None:
                self._download_cache.move_to_end(cache_key)
                return cached
        try:
            response = httpx.get(f"{self.base_url}/{quote(key, safe='/')}", headers=self.headers, timeout=30)
            response.raise_for_status()
            content = response.content
            self._cache_put(key, content)
            return content
        except httpx.HTTPError as error:
            raise RuntimeError("Supabase Storage download failed") from error

    def download_many(self, keys: list[str]) -> dict[str, bytes]:
        """Fetch independent immutable assets concurrently and preserve keys."""
        unique_keys = list(dict.fromkeys(key for key in keys if key))
        if not unique_keys:
            return {}
        with ThreadPoolExecutor(max_workers=min(4, len(unique_keys))) as executor:
            contents = executor.map(self.download, unique_keys)
            return dict(zip(unique_keys, contents, strict=True))

    def _cache_put(self, key: str, content: bytes) -> None:
        cache_key = (self.bucket, key)
        with self._cache_lock:
            self._download_cache[cache_key] = content
            self._download_cache.move_to_end(cache_key)
            while len(self._download_cache) > self._cache_limit:
                self._download_cache.popitem(last=False)

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
            with self._cache_lock:
                for key in prefixes:
                    self._download_cache.pop((self.bucket, key), None)
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
