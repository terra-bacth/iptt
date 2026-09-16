"""Read-only check of the selected database and installed schema.

Run inside the app container after startup. Does not display credentials.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect, text
from database import engine
from models import Base

with engine.connect() as connection:
    assert connection.execute(text("SELECT 1")).scalar_one() == 1
    missing = set(Base.metadata.tables) - set(inspect(connection).get_table_names())
    if missing:
        raise SystemExit(f"Missing tables: {', '.join(sorted(missing))}")
    print(f"PASS: {engine.dialect.name} connected; all {len(Base.metadata.tables)} tables exist")
