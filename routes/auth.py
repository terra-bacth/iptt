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


@router.get("/login", response_class=HTMLResponse)
def login_page():
    return jinja.get_template("login.html").render()


@router.post("/login")
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

    if not user or not pwd_context.verify(password, user.password_hash):
        return jinja.get_template("login.html").render(
            error="Invalid username or password"
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


@router.post("/register")
def register_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    existing = db.query(User).filter(User.username == username).first()

    if existing:
        return jinja.get_template("register.html").render(
            error="User already exists"
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
        current_user=user_session
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