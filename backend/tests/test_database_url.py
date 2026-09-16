from app.db.url import normalize_database_url


def test_normalize_standard_postgresql_url() -> None:
    assert (
        normalize_database_url("postgresql://user:password@example.com/db")
        == "postgresql+psycopg://user:password@example.com/db"
    )


def test_normalize_legacy_postgres_scheme() -> None:
    assert (
        normalize_database_url("postgres://user:password@example.com/db")
        == "postgresql+psycopg://user:password@example.com/db"
    )


def test_normalize_existing_psycopg_url_unchanged() -> None:
    url = "postgresql+psycopg://user:password@example.com/db"
    assert normalize_database_url(url) == url


def test_normalize_preserves_query_parameters() -> None:
    assert (
        normalize_database_url(
            "postgresql://user:pass@host/db?sslmode=require&channel_binding=require"
        )
        == "postgresql+psycopg://user:pass@host/db?sslmode=require&channel_binding=require"
    )


def test_normalize_leaves_unrelated_schemes_unchanged() -> None:
    url = "sqlite+pysqlite:///:memory:"
    assert normalize_database_url(url) == url
