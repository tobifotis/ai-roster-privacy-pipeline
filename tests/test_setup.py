from sqlalchemy import text

from app.db import engine


def test_practice_database_is_not_the_real_one():
    assert engine.url.database == "roster_test"


def test_migrations_built_every_table():
    with engine.connect() as conn:
        tables = set(
            conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            ).scalars()
        )
    expected = {
        "orgs", "users", "demographics", "classes", "enrollments",
        "notes", "api_clients", "alembic_version",
    }
    assert expected <= tables