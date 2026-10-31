"""The service window: serves cleaned rosters to the pretend learning app."""
import hmac
from collections import defaultdict

import jwt
from fastapi import Depends, FastAPI, Form, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import ApiClient, Enrollment, Note, User
from app.security import TOKEN_LIFETIME_SECONDS, create_token, hash_secret, read_token

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


bearer = HTTPBearer(auto_error=False)  # we send our own errors


def current_client(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    """The bouncer: returns the wristband's claims, or stops the request with a 401."""
    if creds is None:
        raise HTTPException(401, "missing_token", headers={"WWW-Authenticate": "Bearer"})
    try:
        return read_token(creds.credentials)
    except jwt.InvalidTokenError:
        raise HTTPException(401, "invalid_token", headers={"WWW-Authenticate": "Bearer"})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/oauth/token")
def issue_token(
    grant_type: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    db: Session = Depends(get_db),
):
    if grant_type != "client_credentials":
        raise HTTPException(status_code=400, detail="unsupported_grant_type")
    client = db.get(ApiClient, client_id)
    # compare in constant time, and compare against a dummy value for unknown apps,
    # so response timing cannot reveal which client IDs exist
    expected = client.secret_hash if client else "0" * 64
    matches = hmac.compare_digest(hash_secret(client_secret), expected)
    if client is None or not matches:
        raise HTTPException(status_code=401, detail="invalid_client")
    return {
        "access_token": create_token(client.client_id, client.tenant_id),
        "token_type": "bearer",
        "expires_in": TOKEN_LIFETIME_SECONDS,
    }


@app.get("/tenants/{tenant_id}/students", response_model=list[StudentOut])
def list_students(
    tenant_id: str,
    claims: dict = Depends(current_client),
    db: Session = Depends(get_db),
):
    # check the wristband's district BEFORE looking anything up
    if claims.get("tenant") != tenant_id or claims.get("scope") != "roster:read":
        raise HTTPException(status_code=403, detail="forbidden")

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