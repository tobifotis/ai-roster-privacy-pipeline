"""Test setup: a practice database rebuilt from the migrations, with a small known data set."""
import os

# Point the app at the practice database BEFORE any app code is imported.
TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://roster:roster_dev_pw@localhost:5432/roster_test",
)
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["ROSTER_JWT_SECRET"] = "test-signing-key-not-a-real-secret"

from datetime import datetime, timezone  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.api import app  # noqa: E402
from app.db import SessionLocal, engine  # noqa: E402
from app.models import ApiClient, Enrollment, Note, SchoolClass, User  # noqa: E402
from app.security import hash_secret  # noqa: E402

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture(scope="session", autouse=True)
def practice_database():
    """Erase the practice database and rebuild its tables from the Alembic migrations."""
    # Safety guard: never wipe anything that is not clearly a test database.
    assert engine.url.database.endswith("_test"), "refusing to wipe a non-test database"
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    command.upgrade(Config("alembic.ini"), "head")
    yield


def _student(tenant, number, given, family):
    sid = f"{tenant}-student-{number}"
    return User(
        tenant_id=tenant, sourced_id=sid, status="active", date_last_modified=NOW,
        enabled_user=True, org_sourced_id=f"{tenant}-school", role="student",
        username=sid, given_name=given, family_name=family, identifier=sid,
        email=f"{given.lower()}@example.com", phone=None, grades="6",
    )


def _note(tenant, number, raw, cleaned):
    student = f"{tenant}-student-{number}"
    return Note(
        tenant_id=tenant, note_id=f"{student}-note", student_sourced_id=student,
        text=raw, text_redacted=cleaned, pii_labels="[]",
    )


@pytest.fixture(autouse=True)
def known_data(practice_database):
    """Before every test: empty the tables, then load a small data set we know exactly."""
    with SessionLocal() as s:
        s.execute(text(
            "TRUNCATE notes, enrollments, demographics, classes, users, api_clients CASCADE"
        ))
        s.add_all([
            _student("district_a", 1, "Maria", "Lopez"),
            _student("district_a", 2, "Sam", "Cole"),
            _student("district_b", 1, "Ana", "Reyes"),
        ])
        s.add(SchoolClass(
            tenant_id="district_a", sourced_id="district_a-class-1", status="active",
            date_last_modified=NOW, title="Math", class_code="M1", class_type="scheduled",
            school_sourced_id="district_a-school",
        ))
        s.flush()
        s.add(Enrollment(
            tenant_id="district_a", sourced_id="district_a-enroll-1", status="active",
            date_last_modified=NOW, class_sourced_id="district_a-class-1",
            school_sourced_id="district_a-school", user_sourced_id="district_a-student-1",
            role="student", is_primary=True, begin_date=None, end_date=None,
        ))
        s.add_all([
            _note("district_a", 1, "Maria Lopez moved to 12 Oak St.", "[PII] moved to [PII]."),
            _note("district_a", 2, "Raw note about Sam Cole", None),  # never cleaned
            _note("district_b", 1, "Ana Reyes called", "[PII] called"),
        ])
        s.add_all([
            ApiClient(client_id="app-a", tenant_id="district_a", name="App A",
                      secret_hash=hash_secret("secret-a")),
            ApiClient(client_id="app-b", tenant_id="district_b", name="App B",
                      secret_hash=hash_secret("secret-b")),
        ])
        s.commit()
    yield


@pytest.fixture
def client():
    return TestClient(app)