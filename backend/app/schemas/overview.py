from datetime import datetime

from pydantic import BaseModel


class PublicUsageSummary(BaseModel):
    unique_record_viewers: int
    total_record_lookups: int
    unique_downloaders: int
    total_downloads: int
    tracking_started_at: datetime | None
