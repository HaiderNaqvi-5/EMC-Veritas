from app.db.session import alembic_config_url, sqlalchemy_database_url


def test_plain_postgres_url_uses_project_driver():
    assert sqlalchemy_database_url("postgresql://user:pass@db.example/project") == "postgresql+psycopg://user:pass@db.example/project"


def test_explicit_sqlalchemy_url_is_unchanged():
    url = "postgresql+psycopg://user:pass@db.example/project"
    assert sqlalchemy_database_url(url) == url


def test_alembic_config_url_escapes_percent_encoded_credentials():
    assert alembic_config_url("postgresql://user:encoded%40secret@db.example/project") == (
        "postgresql+psycopg://user:encoded%%40secret@db.example/project"
    )
