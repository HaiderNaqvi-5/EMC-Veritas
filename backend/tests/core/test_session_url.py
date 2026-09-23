from app.db.session import sqlalchemy_database_url


def test_plain_postgres_url_uses_project_driver():
    assert sqlalchemy_database_url("postgresql://user:pass@db.example/project") == "postgresql+psycopg://user:pass@db.example/project"


def test_explicit_sqlalchemy_url_is_unchanged():
    url = "postgresql+psycopg://user:pass@db.example/project"
    assert sqlalchemy_database_url(url) == url
