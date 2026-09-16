# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra

DATABASE_URL is read from the environment so the same image can run
locally (SQLite file) and on OpenShift (SQLite on a PVC, or PostgreSQL).

Examples:
  sqlite:///iptt.db                         (local, relative file)
  sqlite:////app/data/iptt.db               (absolute path, container + PVC)
  postgresql+psycopg2://user:pass@host/db   (production-grade option)
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///iptt.db")

connect_args = (
    {"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
