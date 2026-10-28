"""Load the synthetic OneRoster CSVs into PostgreSQL, one tenant (district) at a time."""
import csv
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import delete

from app.db import SessionLocal
from app.models import Demographic, Enrollment, Note, Org, SchoolClass, User

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def read_rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def to_dt(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def to_date(value):
    return date.fromisoformat(value) if value else None


def to_bool(value):
    return value.lower() == "true"


def none_if_blank(value):
    return value or None


def load_district(session, tenant):
    folder = DATA_DIR / tenant

    # Reload safely: clear this tenant's rows first (children before parents).
    for model in (Note, Enrollment, Demographic, SchoolClass, User, Org):
        session.execute(delete(model).where(model.tenant_id == tenant))

    orgs = [
        Org(tenant_id=tenant, sourced_id=r["sourcedId"], status=r["status"],
            date_last_modified=to_dt(r["dateLastModified"]), name=r["name"], type=r["type"],
            identifier=r["identifier"], parent_sourced_id=none_if_blank(r["parentSourcedId"]))
        for r in read_rows(folder / "orgs.csv")
    ]
    session.add_all(orgs)
    session.flush()

    users = [
        User(tenant_id=tenant, sourced_id=r["sourcedId"], status=r["status"],
             date_last_modified=to_dt(r["dateLastModified"]), enabled_user=to_bool(r["enabledUser"]),
             org_sourced_id=r["orgSourcedIds"], role=r["role"], username=r["username"],
             given_name=r["givenName"], family_name=r["familyName"], identifier=r["identifier"],
             email=r["email"], phone=none_if_blank(r["phone"]), grades=none_if_blank(r["grades"]))
        for r in read_rows(folder / "users.csv")
    ]
    session.add_all(users)
    session.flush()

    demographics = [
        Demographic(tenant_id=tenant, sourced_id=r["sourcedId"], status=r["status"],
                    date_last_modified=to_dt(r["dateLastModified"]), birth_date=to_date(r["birthDate"]),
                    sex=r["sex"])
        for r in read_rows(folder / "demographics.csv")
    ]
    session.add_all(demographics)

    classes = [
        SchoolClass(tenant_id=tenant, sourced_id=r["sourcedId"], status=r["status"],
                    date_last_modified=to_dt(r["dateLastModified"]), title=r["title"],
                    class_code=r["classCode"], class_type=r["classType"],
                    school_sourced_id=r["schoolSourcedId"])
        for r in read_rows(folder / "classes.csv")
    ]
    session.add_all(classes)
    session.flush()

    enrollments = [
        Enrollment(tenant_id=tenant, sourced_id=r["sourcedId"], status=r["status"],
                   date_last_modified=to_dt(r["dateLastModified"]), class_sourced_id=r["classSourcedId"],
                   school_sourced_id=r["schoolSourcedId"], user_sourced_id=r["userSourcedId"],
                   role=r["role"], is_primary=to_bool(r["primary"]), begin_date=to_date(r["beginDate"]),
                   end_date=to_date(r["endDate"]))
        for r in read_rows(folder / "enrollments.csv")
    ]
    session.add_all(enrollments)

    notes = [
        Note(tenant_id=tenant, note_id=r["noteId"], student_sourced_id=r["studentSourcedId"],
             text=r["text"], pii_labels=r["pii_labels"])
        for r in read_rows(folder / "notes.csv")
    ]
    session.add_all(notes)

    session.commit()
    print(f"{tenant}: loaded {len(orgs)} orgs, {len(users)} users, {len(classes)} classes, "
          f"{len(enrollments)} enrollments, {len(notes)} notes")


if __name__ == "__main__":
    with SessionLocal() as session:
        for district_folder in sorted(p for p in DATA_DIR.iterdir() if p.is_dir()):
            load_district(session, district_folder.name)