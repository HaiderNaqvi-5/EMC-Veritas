from app.core.settings import Settings


def test_cookie_same_site_accepts_cross_site_session_policy() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://user:pass@db.example/emc_veritas",
        supabase_url="https://example.supabase.co",
        session_secret="test-session-secret",
        cookie_same_site="none",
    )

    assert settings.cookie_same_site == "none"
