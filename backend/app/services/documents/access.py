from app.models.domain import DocumentStatus


def is_normally_downloadable(status: DocumentStatus) -> bool:
    return status == DocumentStatus.VALID
