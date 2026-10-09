from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.settings import settings


def sqlalchemy_database_url(url: str) -> str:
    """Use the project-supported psycopg v3 driver for unqualified Postgres URLs."""
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


# Public certificate releases can send dozens of independent student lookups at
# once. Keep enough checked connections available that those short reads do not
# queue behind a ten-connection ceiling; 20 remains well within the managed
# Postgres connection budget used by this service.
engine = create_engine(
    sqlalchemy_database_url(settings.database_url),
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=0,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
