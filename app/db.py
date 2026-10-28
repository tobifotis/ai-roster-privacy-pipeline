import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# This password is for the throwaway local database with synthetic data only.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://roster:roster_dev_pw@localhost:5432/roster",
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)