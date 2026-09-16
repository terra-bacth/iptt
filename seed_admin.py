# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra
"""

# -*- coding: utf-8 -*-
"""
Seed users (Admin, PM, Viewer)
"""

from database import get_db
from models import User
from passlib.context import CryptContext

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


# ✅ Create users
create_user("admin", "admin123", "admin")
create_user("Manoj_PM", "pm123", "pm")
create_user("Manoj_Viewer", "viewer123", "viewer")


db.close()