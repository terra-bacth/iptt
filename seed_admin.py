# -*- coding: utf-8 -*-
"""
Seed users (Admin, PM, Viewer)

- Creates DB tables first (safe to run multiple times)
- Set SEED_ADMIN_PASSWORD to override the default admin password
"""

import os

from database import Base, engine, get_db
from models import User  # noqa: F401  (import registers all models on Base)
from passlib.context import CryptContext

# ✅ Ensure tables exist (idempotent)
Base.metadata.create_all(bind=engine)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

db = next(get_db())


def create_user(username, password, role):
    existing = db.query(User).filter(User.username == username).first()

    if existing:
        print(f"ℹ User '{username}' already exists")
        return

    user = User(
        username=username,
        password_hash=pwd_context.hash(password),
        role=role,
        is_active=True
    )

    db.add(user)
    db.commit()

    print(f"✅ Created {role} user: {username}")


admin_password = os.getenv("SEED_ADMIN_PASSWORD", "admin123")

# ✅ Create users
create_user("admin", admin_password, "admin")
create_user("Manoj_PM", "pm123", "pm")
create_user("Manoj_Viewer", "viewer123", "viewer")


db.close()
print("🌱 Seeding complete")
