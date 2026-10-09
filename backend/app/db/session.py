from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.settings import settings


def sqlalchemy_database_url(url: str) -> str:
    """Use the project-supported psycopg v3 driver for unqualified Postgres URLs."""
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


database_url = sqlalchemy_database_url(settings.database_url)

# Supabase's transaction pooler (port 6543) multiplexes short database
# transactions itself. Retaining application-side connections in that mode
# consumes client slots and turns a sudden portal release into a queue.
# Session/direct connections retain the bounded local pool used in production.
if make_url(database_url).port == 6543:
    engine = create_engine(database_url, poolclass=NullPool)
else:
    engine = create_engine(database_url, pool_pre_ping=True, pool_size=5, max_overflow=5)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
