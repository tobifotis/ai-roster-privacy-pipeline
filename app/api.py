"""The service window: serves cleaned rosters to the pretend learning app."""
from collections import defaultdict

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Enrollment, Note, User

app = FastAPI(title="Roster API", description="Serves rosters with private details removed.")


class NoteOut(BaseModel):
    note_id: str
    text: str


class StudentOut(BaseModel):
    sourced_id: str
    grades: str | None
    class_ids: list[str]
    notes: list[NoteOut]


def get_db():
    with SessionLocal() as session:
        yield session


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/tenants/{tenant_id}/students", response_model=list[StudentOut])
def list_students(tenant_id: str, db: Session = Depends(get_db)):
    students = db.scalars(
        select(User)
        .where(User.tenant_id == tenant_id, User.role == "student")
        .order_by(User.sourced_id)
    ).all()
    if not students:
        raise HTTPException(status_code=404, detail="Unknown district")

    # one query for all enrollments and one for all notes, then match them up in Python
    class_ids = defaultdict(list)
    for e in db.scalars(select(Enrollment).where(Enrollment.tenant_id == tenant_id)):
        class_ids[e.user_sourced_id].append(e.class_sourced_id)

    notes = defaultdict(list)
    for n in db.scalars(
        select(Note).where(Note.tenant_id == tenant_id, Note.text_redacted.is_not(None))
    ):
        notes[n.student_sourced_id].append(NoteOut(note_id=n.note_id, text=n.text_redacted))

    return [
        StudentOut(
            sourced_id=s.sourced_id,
            grades=s.grades,
            class_ids=class_ids[s.sourced_id],
            notes=notes[s.sourced_id],
        )
        for s in students
    ]