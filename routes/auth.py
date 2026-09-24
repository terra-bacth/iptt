# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra
"""

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jinja2 import Environment, FileSystemLoader

from database import get_db
from models import User

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
jinja = Environment(loader=FileSystemLoader("templates"))


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        import bcrypt
        pw_bytes = plain_password.encode('utf-8')[:72] if isinstance(plain_password, str) else plain_password[:72]
        hash_bytes = password_hash.encode('utf-8') if isinstance(password_hash, str) else password_hash
        return bcrypt.checkpw(pw_bytes, hash_bytes)
    except Exception:
        try:
            return pwd_context.verify(plain_password[:72], password_hash)
        except Exception:
            return False


@router.get("/login", response_class=HTMLResponse)
def login_page():
    return jinja.get_template("login.html").render()


@router.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(User.username == username, User.is_active == True)
        .first()
    )

    if not user or not verify_password(password, user.password_hash):
        return HTMLResponse(
            content=jinja.get_template("login.html").render(
                error="Username or password incorrect"
            ),
            status_code=200
        )

    request.session["user"] = {
        "id": user.id,
        "username": user.username,
        "role": user.role,
    }

    return RedirectResponse("/home", status_code=302)

@router.get("/register", response_class=HTMLResponse)
def register_page():
    return jinja.get_template("register.html").render()


@router.post("/register", response_class=HTMLResponse)
def register_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    existing = db.query(User).filter(User.username == username).first()

    if existing:
        return HTMLResponse(
            content=jinja.get_template("register.html").render(
                error="User already exists"
            ),
            status_code=200
        )

    hashed_password = pwd_context.hash(password)

    new_user = User(
        username=username,
        password_hash=hashed_password,
        role="viewer",
        is_active=True
    )

    db.add(new_user)
    db.commit()

    return RedirectResponse("/login?success=registered", status_code=302)

@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)

@router.get("/users", response_class=HTMLResponse)
def manage_users(request: Request, db: Session = Depends(get_db)):

    user_session = request.session.get("user")

    # ✅ Only admin allowed
    if not user_session or user_session["role"] != "admin":
        return RedirectResponse("/home?error=admin_required", status_code=303)

    users = db.query(User).all()

    return jinja.get_template("users.html").render(
        users=users,
        current_user=user_session,
        # The shared navigation reads `user` to decide on the admin entries.
        user=user_session
    )

@router.post("/users/update-role")
def update_user_role(
    request: Request,
    user_id: int = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db)
):

    user_session = request.session.get("user")

    # ✅ Only admin
    if not user_session or user_session["role"] != "admin":
        return RedirectResponse("/home?error=admin_required", status_code=303)

    user = db.query(User).filter(User.id == user_id).first()

    if user:
        user.role = role
        db.commit()

    return RedirectResponse("/users", status_code=303)

@router.post("/users/change-password")
def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    # 1. Enforce active user validation check
    user_session = request.session.get("user")
    if not user_session:
        return RedirectResponse("/login", status_code=302)

    # 2. Extract database record context
    user = db.query(User).filter(User.id == user_session["id"]).first()
    if not user:
        return RedirectResponse("/login", status_code=302)

    # 3. Cryptographic Assertion: Validate existing hash integrity
    if not pwd_context.verify(current_password, user.password_hash):
        return HTMLResponse(
            content=jinja.get_template("profile.html").render(
                user=user_session,
                error="❌ Validation Failed: The current password you entered is incorrect."
            ),
            status_code=200
        )

    # 4. Input Integrity Assertion: Validate string matching
    if new_password != confirm_password:
        return HTMLResponse(
            content=jinja.get_template("profile.html").render(
                user=user_session,
                error="❌ Operational Conflict: New password and confirmation entries do not match."
            ),
            status_code=200
        )

    # 5. Cryptography Transformation: Compute new safe bcrypt hash
    user.password_hash = pwd_context.hash(new_password)
    
    # 6. Database Commit Execution
    db.commit()

    return HTMLResponse(
        content=jinja.get_template("profile.html").render(
            user=user_session,
            success="✅ Security credentials updated successfully inside the system."
        ),
        status_code=200
    )