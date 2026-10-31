from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKeyConstraint, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Org(Base):
    __tablename__ = "orgs"
    tenant_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    sourced_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    status: Mapped[str] = mapped_column(String(20))
    date_last_modified: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(20))
    identifier: Mapped[str] = mapped_column(String(50))
    parent_sourced_id: Mapped[str | None] = mapped_column(String(100))


class User(Base):
    __tablename__ = "users"
    tenant_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    sourced_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    status: Mapped[str] = mapped_column(String(20))
    date_last_modified: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    enabled_user: Mapped[bool] = mapped_column(Boolean)
    org_sourced_id: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20))
    username: Mapped[str] = mapped_column(String(100))
    given_name: Mapped[str] = mapped_column(String(100))
    family_name: Mapped[str] = mapped_column(String(100))
    identifier: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(50))
    grades: Mapped[str | None] = mapped_column(String(20))


class Demographic(Base):
    __tablename__ = "demographics"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "sourced_id"], ["users.tenant_id", "users.sourced_id"]),
    )
    tenant_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    sourced_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    status: Mapped[str] = mapped_column(String(20))
    date_last_modified: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    birth_date: Mapped[date] = mapped_column(Date)
    sex: Mapped[str] = mapped_column(String(20))


class SchoolClass(Base):
    __tablename__ = "classes"
    tenant_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    sourced_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    status: Mapped[str] = mapped_column(String(20))
    date_last_modified: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    title: Mapped[str] = mapped_column(String(200))
    class_code: Mapped[str] = mapped_column(String(50))
    class_type: Mapped[str] = mapped_column(String(50))
    school_sourced_id: Mapped[str] = mapped_column(String(100))


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "class_sourced_id"], ["classes.tenant_id", "classes.sourced_id"]),
        ForeignKeyConstraint(["tenant_id", "user_sourced_id"], ["users.tenant_id", "users.sourced_id"]),
    )
    tenant_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    sourced_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    status: Mapped[str] = mapped_column(String(20))
    date_last_modified: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    class_sourced_id: Mapped[str] = mapped_column(String(100))
    school_sourced_id: Mapped[str] = mapped_column(String(100))
    user_sourced_id: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20))
    is_primary: Mapped[bool] = mapped_column(Boolean)
    begin_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)


class Note(Base):
    __tablename__ = "notes"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "student_sourced_id"], ["users.tenant_id", "users.sourced_id"]),
    )
    tenant_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    note_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    student_sourced_id: Mapped[str] = mapped_column(String(100))
    text: Mapped[str] = mapped_column(Text)
    text_redacted: Mapped[str | None] = mapped_column(Text)  # cleaned copy, filled by a script
    pii_labels: Mapped[str] = mapped_column(Text)  # JSON list, the answer key for scoring

class ApiClient(Base):
    """An app that is allowed to log in to the API. Only a hash of its secret is stored."""
    __tablename__ = "api_clients"
    client_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(50))  # the one district this app may read
    name: Mapped[str] = mapped_column(String(200))
    secret_hash: Mapped[str] = mapped_column(String(64))  # SHA-256 of the secret, as hex