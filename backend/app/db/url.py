"""Normalize provider DATABASE_URL schemes for SQLAlchemy + psycopg 3."""


def normalize_database_url(database_url: str) -> str:
    """Map common PostgreSQL URL schemes to the explicit psycopg 3 dialect.

    Only the scheme is rewritten. Credentials, host, path, and query
    parameters are preserved exactly.
    """
    if database_url.startswith("postgres://"):
        return "postgresql+psycopg://" + database_url.removeprefix("postgres://")
    if database_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + database_url.removeprefix("postgresql://")
    return database_url
