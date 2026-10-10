from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.admin.dependencies import current_active_admin
from app.db.session import get_db
from app.models.domain import Admin, PublicStudentUsage
from app.schemas.overview import PublicUsageSummary

router = APIRouter(prefix="/overview", tags=["overview"])


@router.get("/public-usage", response_model=PublicUsageSummary)
def public_usage_summary(
    db: Session = Depends(get_db),
    admin: Admin = Depends(current_active_admin),
) -> PublicUsageSummary:
    del admin
    row = db.execute(
        select(
            func.count().filter(PublicStudentUsage.lookup_count > 0),
            func.coalesce(func.sum(PublicStudentUsage.lookup_count), 0),
            func.count().filter(PublicStudentUsage.download_count > 0),
            func.coalesce(func.sum(PublicStudentUsage.download_count), 0),
            func.min(PublicStudentUsage.created_at),
        )
    ).one()
    return PublicUsageSummary(
        unique_record_viewers=row[0],
        total_record_lookups=row[1],
        unique_downloaders=row[2],
        total_downloads=row[3],
        tracking_started_at=row[4],
    )
