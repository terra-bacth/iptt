# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra
"""

from starlette.middleware.sessions import SessionMiddleware
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from io import BytesIO
from xhtml2pdf import pisa
from fastapi.responses import Response
from contextlib import contextmanager
from jinja2 import Environment, FileSystemLoader
from datetime import datetime, timedelta, date
from io import BytesIO
from fastapi.responses import StreamingResponse
import pandas as pd
import os

from auth.dependencies import require_login
from database import engine, get_db
from models import Base, Scope, Task, Project, TaskExecution
from services import programme_service
from services.task_execution_service import (
    complete_task_execution,
    get_project_delay_heatmap,
    get_scope_progress,
    get_project_executive_summary,
    get_scope_delay_summary,
    get_task_execution_with_delay,
    get_task_execution_for_scope,
    get_scope_by_id,
)
from services.reporting.pdf_export import (
    generate_executive_pdf
)
from services.planner_data_adapter import build_scope_df, build_tasks_df
from services.runbook_scheduler.planner import generate_project_plan
from services.calendar_utils import HOLIDAYS
from routes import programme, project, task, scope
from routes import execution
from routes.execution import get_executive_summary
from routes import leadership_actions
from fastapi.templating import Jinja2Templates

app = FastAPI()

templates = Jinja2Templates(
    directory="templates"
)

# ---------------- APP SETUP ----------------
app = FastAPI(
    title="Integrated Project Tracking Tool (IPTT)",
    version="1.0"
)

app.include_router(
    leadership_actions.router
)

Base.metadata.create_all(bind=engine)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "iptt-dev-secret-change-me")
)

@app.exception_handler(HTTPException)
async def auth_exception_handler(request: Request, exc: HTTPException):

    # ✅ Redirect unauthenticated users to login
    if exc.status_code == 401:
        return RedirectResponse(url="/login", status_code=302)

    # ✅ Optional: handle forbidden access
    if exc.status_code == 403:
        return RedirectResponse(url="/home?error=forbidden", status_code=302)

    # ✅ Default fallback (optional)
    raise exc
from routes import auth
app.include_router(programme.router, prefix="/api/programmes", tags=["Programmes"])
app.include_router(project.router, prefix="/api/projects", tags=["Projects"])
app.include_router(task.router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(scope.router, tags=["Scope"])
app.include_router(execution.router)
app.include_router(auth.router)

app.mount("/static", StaticFiles(directory="static"), name="static")

jinja_env = Environment(loader=FileSystemLoader("templates"))

# ---------------- DB CONTEXT ----------------
@contextmanager
def get_db_ctx():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

# ---------------- UI ROUTES ----------------
from fastapi.responses import HTMLResponse

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_ui(request: Request):
    user = require_login(request)

    with get_db_ctx() as db:
        
        if user["role"] == "admin":
        
            programmes = programme_service.get_programmes(db)
        
        elif user["role"] == "pm":
        
            assigned_project_ids = db.query(
                ProjectAssignment.project_id
            ).filter(
                ProjectAssignment.user_id == user["id"]
            ).all()
        
            assigned_project_ids = [
                p[0] for p in assigned_project_ids
            ]
        
            assigned_projects = db.query(Project).filter(
                Project.id.in_(assigned_project_ids)
            ).all()
        
            programme_ids = list(set([
                p.programme_id for p in assigned_projects
            ]))
        
            programmes = db.query(Programme).filter(
                Programme.id.in_(programme_ids)
            ).all()
        
        else:
        
            programmes = programme_service.get_programmes(db)


        data = []
        for p in programmes:
            projects = programme_service.get_projects(db, p.id)
            total = len(projects)
            planned = sum(1 for proj in projects if proj.project_start_date)
            percent = int((planned / total) * 100) if total else 0

            data.append({
            
                "programme_id": p.id,
            
                "programme": p.name,
            
                "total": total,
            
                "planned": planned,
            
                "percent": percent
            })
            
    html = jinja_env.get_template("dashboard.html").render(
        user=user,
        data=data
    )

    return HTMLResponse(content=html)



@app.get("/")
def home_redirect():
    return RedirectResponse("/programmes", status_code=302)



@app.get("/project/{project_id}/execution", response_class=HTMLResponse)
def execution_ui(project_id: int, request: Request):

    user = require_login(request)

    with get_db_ctx() as db:

        # ✅ SECURITY CHECK
        if not validate_project_access(
            db,
            user,
            project_id
        ):
            return RedirectResponse(
                "/home?error=not_authorized",
                status_code=303
            )

        # ✅ 1. Get project
        project = db.query(Project).filter(
            Project.id == project_id
        ).first()

        project_name = project.name if project else "Project"

        # ✅ 2. Get programme
        programme_name = ""

        if project and project.programme_id:

            programme = db.query(Programme).filter(
                Programme.id == project.programme_id
            ).first()

            programme_name = (
                programme.name if programme else "Programme"
            )

        # ✅ 3. Get scope
        scopes = db.query(Scope).filter(
            Scope.project_id == project_id
        ).all()

        # ✅ 4. Group by circle
        circle_map = {}

        for s in scopes:

            circle = s.circle if s.circle else "Unknown"

            if circle not in circle_map:
                circle_map[circle] = []

            exec_rows = get_task_execution_for_scope(
                db,
                s.id
            )

            if not exec_rows:
                status = "Not Started"

            elif all(r[0].status == "Completed" for r in exec_rows):
                status = "Completed"

            elif any(r[0].delay_days > 0 for r in exec_rows):
                status = "At Risk"

            else:
                status = "In Progress"

            circle_map[circle].append({

                "scope_id": s.id,

                "node_name": s.node_id,

                "facility_name": s.facility_name,

                "status": status
            })

    return HTMLResponse(

        jinja_env.get_template(
            "execution_dashboard.html"
        ).render(

            project_id=project_id,

            project_name=project_name,

            programme_name=programme_name,

            circles=circle_map,

            user=user
        )
    )
from auth.dependencies import require_admin

@app.post("/", response_class=RedirectResponse)
def create_programme_ui(
    request: Request,
    name: str = Form(...)
):
    # ✅ ADD THIS (CRITICAL FIX)
    
    user = request.session.get("user")
    
    if user.get("role") != "admin":
        return RedirectResponse("/programmes?error=admin_required", status_code=303)


    with get_db_ctx() as db:
        programme_service.create_programme(db, name, "Active")

    return RedirectResponse("/", status_code=303)


@app.get("/projects")
def projects_entry(request: Request, programme_id: str | None = None):
    """Entry point for /projects.

    The programme id is optional. The home page form omits it while a programme
    list is empty, so instead of failing request validation the user is
    forwarded to the first programme they can open, or to the programme list.
    """

    user = require_login(request)

    if programme_id and programme_id.strip().isdigit():
        return RedirectResponse(f"/projects/{int(programme_id)}", status_code=303)

    with get_db_ctx() as db:

        if user["role"] == "admin":
            programmes = db.query(Programme).order_by(Programme.name).all()
        elif user["role"] == "pm":
            project_ids = [
                a.project_id
                for a in db.query(ProjectAssignment).filter(
                    ProjectAssignment.user_id == user["id"]
                ).all()
            ]
            programme_ids = {
                p.programme_id
                for p in db.query(Project).filter(Project.id.in_(project_ids)).all()
                if p.programme_id
            }
            programmes = [
                p for p in db.query(Programme).order_by(Programme.name).all()
                if p.id in programme_ids
            ]
        else:
            programmes = db.query(Programme).order_by(Programme.name).all()

        if len(programmes) == 1:
            return RedirectResponse(f"/projects/{programmes[0].id}", status_code=303)

    return RedirectResponse("/programmes", status_code=303)


@app.get("/projects/{programme_id}", response_class=HTMLResponse)
def projects_ui(programme_id: int, request: Request):

    user = require_login(request)

    with get_db_ctx() as db:

        # ✅ SECURITY CHECK
        if not validate_programme_access(
            db,
            user,
            programme_id
        ):
            return RedirectResponse(
                "/home?error=not_authorized",
                status_code=303
            )

        programme = db.query(Programme).filter(
            Programme.id == programme_id
        ).first()

        programme_name = (
            programme.name if programme else "Programme"
        )

        projects = programme_service.get_projects(
            db,
            programme_id
        )

        # ✅ PM sees assigned projects only
        if user["role"] == "pm":

            projects = [

                p for p in projects

                if validate_project_access(
                    db,
                    user,
                    p.id
                )
            ]

        users = db.query(User).filter(
            User.role == "pm"
        ).all()

        project_users_map = {}

        for p in projects:

            assignments = db.query(ProjectAssignment).filter(
                ProjectAssignment.project_id == p.id
            ).all()

            if not assignments:

                project_users_map[p.id] = "None"

                continue

            user_ids = [a.user_id for a in assignments]

            users_list = db.query(User).filter(
                User.id.in_(user_ids)
            ).all()

            project_users_map[p.id] = (

                ", ".join([
                    u.username.strip()
                    for u in users_list
                ])

                if users_list
                else "None"
            )

        project_status = {}

        for p in projects:

            scope_done = db.query(Scope).filter(
                Scope.project_id == p.id
            ).count() > 0

            tasks_done = db.query(Task).filter(
                Task.project_id == p.id
            ).count() > 0

            plan_done = (
                p.project_start_date is not None
            )

            setup_completed = (
                scope_done and
                tasks_done and
                plan_done
            )

            progress_score = (
                int(scope_done) +
                int(tasks_done) +
                int(plan_done)
            )

            progress_percent = int(
                (progress_score / 3) * 100
            )

            project_status[p.id] = {

                "scope_done": scope_done,

                "tasks_done": tasks_done,

                "plan_done": plan_done,

                "setup_completed": setup_completed,

                "progress": progress_percent
            }

    return HTMLResponse(

        jinja_env.get_template(
            "projects.html"
        ).render(

            projects=projects,

            programme_id=programme_id,

            programme_name=programme_name,

            project_status=project_status,

            users=users,

            project_users_map=project_users_map,

            user=request.session.get("user")
        )
    )

@app.post("/projects/{programme_id}", response_class=RedirectResponse)
def create_project_ui(
    programme_id: int,
    request: Request,
    name: str = Form(...),
    priority: str = Form(...)
):
    
    user = request.session.get("user")
    
    # ✅ Block only Viewer
    if user.get("role") == "viewer":
        return RedirectResponse(
            f"/projects/{programme_id}?error=not_allowed",
            status_code=303
        )

    from models import ProjectAssignment
    
    with get_db_ctx() as db:
    
        # ✅ 1. Create project
        project = programme_service.create_project(
            db, programme_id, name, priority, "Not Started"
        )
    
        # ✅ 2. Get current user
        user = request.session.get("user")
    
        # ✅ 3. Assign project to creator
        assignment = ProjectAssignment(
            project_id=project.id,
            user_id=user["id"]
        )
    
        db.add(assignment)
        db.commit()

    return RedirectResponse(f"/projects/{programme_id}", status_code=303)

# ---------------- ✅ SCOPE UI ROUTE (FIX) ----------------

@app.get("/project/{project_id}/scopes", response_class=HTMLResponse)

def project_scopes_ui(project_id: int, request: Request):
    # ✅ LOGIN CHECK
    
    user = require_login(request)
    with get_db_ctx() as db:
        scopes = (
            db.query(Scope)
            .filter(Scope.project_id == project_id)
            .order_by(Scope.priority)
            .all()
        )
        project = db.query(Project).filter(
            Project.id == project_id
        ).first()
        
        return jinja_env.get_template("scopes.html").render(
            scopes=scopes,
            project_id=project_id,
            programme_id=project.programme_id,
            user=user
        )

# ---------------- TASK ROUTES ----------------

@app.get("/tasks/{project_id}", response_class=HTMLResponse)
def tasks_ui(project_id: int, request: Request):

    user = require_login(request)

    with get_db_ctx() as db:

        # ===================================
        # FETCH ALL TASKS
        # ===================================

        raw_tasks = db.query(Task).filter(
            Task.project_id == project_id
        ).order_by(
            Task.id.asc()
        ).all()

        # ===================================
        # BUILD UNIQUE WORKFLOW TASKS
        # ===================================

        unique_tasks = []

        seen = set()

        for t in raw_tasks:

            key = (
                t.name,
                t.duration_days,
                t.predecessor_task_id
            )

            if key not in seen:

                seen.add(key)

                unique_tasks.append(t)

        # ===================================
        # BUILD TASK ID → TASK NAME MAP
        # ===================================

        task_name_map = {}

        for t in unique_tasks:

            task_name_map[t.id] = t.name

        # ===================================
        # GENERATE SEQUENCE NUMBERS
        # ===================================

        workflow_tasks = []

        seq = 1

        for t in unique_tasks:

            predecessor_name = "—"

            if t.predecessor_task_id:

                predecessor_name = task_name_map.get(
                    t.predecessor_task_id,
                    f"Task #{t.predecessor_task_id}"
                )

            workflow_tasks.append({

                "seq": seq,

                "id": t.id,

                "name": t.name,

                "duration_days": t.duration_days,

                "dependency": predecessor_name,

                "flow": (
                    f"{predecessor_name} → {t.name}"
                    if predecessor_name != "—"
                    else f"Start → {t.name}"
                ),

                "is_critical": t.is_critical
            })

            seq += 1
            
        project = db.query(Project).filter(
            Project.id == project_id
        ).first()
        return jinja_env.get_template(
            "tasks.html"
        ).render(

            tasks=workflow_tasks,

            project_id=project_id,
            
            programme_id=project.programme_id,

            user=user
        )


@app.post("/tasks/{project_id}", response_class=RedirectResponse)
def create_task_ui(
    project_id: int,
    request: Request,
    name: str = Form(...),
    duration_days: int = Form(...),
    assigned_to: str = Form(""),
    owner_role: str = Form(""),
    predecessor_task_no: int | None = Form(None),
    is_prerequisite: bool = Form(False),
):
    require_admin(request)
    predecessor_task_id = predecessor_task_no if predecessor_task_no else None

    with get_db_ctx() as db:
        programme_service.create_task(
            db=db,
            project_id=project_id,
            name=name,
            duration_days=duration_days,
            assigned_to=assigned_to,
            owner_role=owner_role,
            predecessor_task_id=predecessor_task_id,
            is_prerequisite=is_prerequisite
        )

    return RedirectResponse(f"/tasks/{project_id}", status_code=303)


# ---------------- DAY‑0 PLAN DOWNLOAD ----------------

@app.get("/project/{project_id}/plan/download")
def download_day_0_plan(project_id: int):

    with get_db_ctx() as db:
        project = db.query(Project).filter(Project.id == project_id).first()

        if not project or not project.project_start_date:
            return HTMLResponse(
                "Project initiation date not set.",
                status_code=400
            )

        scope_df = build_scope_df(db, project_id)
        tasks_df = build_tasks_df(db, project_id)

        plan_df = generate_project_plan(
            kickoff_date=project.project_start_date,
            scope_df=scope_df,
            tasks_df=tasks_df,
            holidays=HOLIDAYS
        )
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            plan_df.to_excel(writer, index=False, sheet_name="Day0_Plan")
        
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition":
                f'attachment; filename="Day0_Project_{project_id}_Plan.xlsx"'
            }
        )


from fastapi.responses import HTMLResponse, RedirectResponse
from utils.access_control import is_project_assigned

@app.get("/scope/{scope_id}/execution", response_class=HTMLResponse)
def scope_execution_ui(scope_id: int, request: Request):
    user = require_login(request)

    # 1. Open and close database operations as fast as possible
    with get_db_ctx() as db:
        scope = get_scope_by_id(db, scope_id)

        # ✅ SAFETY CHECK
        if not scope:
            return RedirectResponse("/home?error=invalid_scope", status_code=303)

        project_id = scope.project_id
        program_id = scope.program_id if hasattr(scope, 'program_id') else 6

        # ✅ ASSIGNMENT ENFORCEMENT (PM ONLY)
        if user["role"] == "pm":
            if not is_project_assigned(db, project_id, user["id"]):
                return RedirectResponse(
                    "/home?error=not_assigned",
                    status_code=303
                )

    # 🚀 FIX: Moved outside the 'with' block to ensure clean data state execution context
    return HTMLResponse(
        jinja_env.get_template("execution.html").render(
            request=request, 
            project_id=project_id,
            program_id=program_id,  # 🔥 Added to fix the 'Projects' breadcrumb loop!
            scope_id=scope_id,
            role=user.get("role", "viewer"),  
            user={
                "role": user.get("role", "viewer"),
                "username": user.get("username", "Manoj Mishra")
            } 
        )
    )

from auth.dependencies import require_pm_or_admin

@app.post("/scope/{scope_id}/execution/update")
def update_execution(scope_id: int, request: Request):
    
 user = require_pm_or_admin(request)

 form = request.form()

 with get_db_ctx() as db:

    # ===================================
    # GET SCOPE
    # ===================================

    scope = db.query(Scope).filter(
        Scope.id == scope_id
    ).first()

    if not scope:

        return RedirectResponse(
            "/home",
            status_code=303
        )

    # ===================================
    # SECURITY CHECK
    # ===================================

    if not validate_project_access(
        db,
        user,
        scope.project_id
    ):

        return RedirectResponse(
            "/home?error=not_authorized",
            status_code=303
        )

    # ===================================
    # GET EXECUTIONS
    # ===================================

    executions = get_task_execution_for_scope(
        db,
        scope_id
    )

    # ===================================
    # UPDATE EXECUTIONS
    # ===================================

    for row in executions:

        row.actual_start = (
            form.get(f"actual_start_{row.id}") or None
        )

        row.actual_finish = (
            form.get(f"actual_finish_{row.id}") or None
        )

        row.status = form.get(
            f"status_{row.id}"
        )

        row.delay_reason = form.get(
            f"delay_reason_{row.id}"
        )

        # ===================================
        # STATUS LOGIC
        # ===================================

        if not row.actual_start and not row.actual_finish:

            row.status = "Not Started"

        elif row.actual_start and not row.actual_finish:

            row.status = "In Progress"

        elif row.actual_finish:

            row.status = "Completed"

        # ===================================
        # DELAY CALCULATION
        # ===================================

        if row.actual_finish and row.planned_finish:

            delay = (
                row.actual_finish -
                row.planned_finish
            ).days

            row.delay_days = max(0, delay)

        else:

            row.delay_days = 0

    db.commit()

 return RedirectResponse(
    url=f"/scope/{scope_id}/execution",
    status_code=303
)


from models import (
    Project,
    Scope,
    Task,
    TaskExecution,
    Programme,
    ProjectAssignment,
    User
)

from routes.execution import get_executive_summary

# =========================================
# ACCESS CONTROL HELPERS
# =========================================

def validate_project_access(db, user, project_id):

    # ✅ Admin full access
    if user["role"] == "admin":
        return True

    # ✅ PM only assigned projects
    if user["role"] == "pm":

        assignment = db.query(ProjectAssignment).filter(
            ProjectAssignment.project_id == project_id,
            ProjectAssignment.user_id == user["id"]
        ).first()

        return assignment is not None

    # ✅ Viewer = read only access
    return True


def validate_programme_access(db, user, programme_id):

    # ✅ Admin full access
    if user["role"] == "admin":
        return True

    # ✅ PM only assigned programme
    if user["role"] == "pm":

        assigned_projects = db.query(ProjectAssignment).filter(
            ProjectAssignment.user_id == user["id"]
        ).all()

        project_ids = [a.project_id for a in assigned_projects]

        projects = db.query(Project).filter(
            Project.id.in_(project_ids)
        ).all()

        allowed_programmes = list(set([
            p.programme_id for p in projects
            if p.programme_id
        ]))

        return programme_id in allowed_programmes

    return True

@app.get("/home", response_class=HTMLResponse)
def home_ui(request: Request):

    user = require_login(request)

    from models import ProjectAssignment, User

    with get_db_ctx() as db:

        # ===================================
        # ROLE-BASED PROJECT ACCESS
        # ===================================

        if user["role"] == "admin":

            projects = db.query(Project).all()

            programmes = programme_service.get_programmes(db)

        elif user["role"] == "pm":

            # ✅ Assigned project IDs
            assigned_project_ids = db.query(
                ProjectAssignment.project_id
            ).filter(
                ProjectAssignment.user_id == user["id"]
            ).all()

            assigned_project_ids = [
                p[0] for p in assigned_project_ids
            ]

            # ✅ Only assigned projects
            projects = db.query(Project).filter(
                Project.id.in_(assigned_project_ids)
            ).all()

            # ✅ Only related programmes
            programme_ids = list(set([
                p.programme_id for p in projects
                if p.programme_id
            ]))

            programmes = db.query(Programme).filter(
                Programme.id.in_(programme_ids)
            ).all()

        else:

            # ✅ VIEWER
            projects = db.query(Project).all()

            programmes = programme_service.get_programmes(db)

        # ===================================
        # SEPARATE BUCKETS
        # ===================================

        setup_projects = []

        programme_projects = {}

        completed_projects = []

        # ===================================
        # PROCESS PROJECTS
        # ===================================

        for p in projects:

            # -----------------------------------
            # EXECUTION START CHECK
            # -----------------------------------

            execution_started = db.query(TaskExecution).filter(
                TaskExecution.project_id == p.id
            ).count() > 0

            exec_summary = get_executive_summary(
                p.id,
                db
            )

            # -----------------------------------
            # PROGRAMME NAME
            # -----------------------------------

            programme_name = "Unknown"

            if p.programme_id:

                programme = db.query(Programme).filter(
                    Programme.id == p.programme_id
                ).first()

                programme_name = (
                    programme.name if programme else "Unknown"
                )

            # -----------------------------------
            # PM NAME
            # -----------------------------------

            assignments = db.query(ProjectAssignment).filter(
                ProjectAssignment.project_id == p.id
            ).all()

            pm_names = []

            for a in assignments:

                user_obj = db.query(User).filter(
                    User.id == a.user_id
                ).first()

                if user_obj:

                    pm_names.append(user_obj.username)

            pm_name = (
                ", ".join(pm_names)
                if pm_names
                else "Unassigned"
            )

            # -----------------------------------
            # PROJECT OBJECT
            # -----------------------------------

            project_obj = {

                "project_id": p.id,

                "programme_id": p.programme_id,

                "project_name": p.name,

                "pm": pm_name,

                "at_risk": (
                    exec_summary["at_risk_nodes"] > 0
                )
            }

            # -----------------------------------
            # SETUP COMPLETENESS CHECK
            # -----------------------------------

            scope_done = db.query(Scope).filter(
                Scope.project_id == p.id
            ).count() > 0

            tasks_done = db.query(Task).filter(
                Task.project_id == p.id
            ).count() > 0

            plan_done = (
                p.project_start_date is not None
            )

            setup_completed = (

                scope_done and
                tasks_done and
                plan_done
            )

            # -----------------------------------
            # COMPLETED CHECK
            # -----------------------------------

            incomplete_tasks = db.query(
                TaskExecution
            ).filter(

                TaskExecution.project_id == p.id,

                TaskExecution.status != "Completed"

            ).count()

            all_completed = (

                execution_started and
                incomplete_tasks == 0
            )

            # -----------------------------------
            # CLASSIFICATION
            # -----------------------------------

            # ✅ Setup Phase

            if not setup_completed:

                setup_projects.append(
                    project_obj
                )

            # ✅ Completed

            elif all_completed:

                completed_projects.append(
                    project_obj
                )

            # ✅ Ongoing

            else:

                if programme_name not in programme_projects:

                    programme_projects[
                        programme_name
                    ] = []

                programme_projects[
                    programme_name
                ].append(project_obj)

    # ===================================
    # RENDER
    # ===================================

    return HTMLResponse(

        jinja_env.get_template(
            "home.html"
        ).render(

            user=user,

            programmes=programmes,

            setup_projects=setup_projects,

            programme_projects=programme_projects,

            completed_projects=completed_projects
        )
    )

@app.get("/programmes", response_class=HTMLResponse)
def programmes_ui(request: Request):
    user = require_login(request)

    with get_db_ctx() as db:
        
        if user["role"] == "admin":
        
            programmes = programme_service.get_programmes(db)
        
        elif user["role"] == "pm":
        
            assigned_project_ids = db.query(
                ProjectAssignment.project_id
            ).filter(
                ProjectAssignment.user_id == user["id"]
            ).all()
        
            assigned_project_ids = [
                p[0] for p in assigned_project_ids
            ]
        
            assigned_projects = db.query(Project).filter(
                Project.id.in_(assigned_project_ids)
            ).all()
        
            programme_ids = list(set([
                p.programme_id for p in assigned_projects
            ]))
        
            programmes = db.query(Programme).filter(
                Programme.id.in_(programme_ids)
            ).all()
        
        else:
        
            programmes = programme_service.get_programmes(db)


        programme_project_counts = {}
        programme_summary = {}

        for p in programmes:
            projects = programme_service.get_projects(db, p.id)

            total = len(projects)
            completed = 0
            in_progress = 0
            at_risk = 0

            for proj in projects:
                exec_summary = get_executive_summary(proj.id, db)

                if exec_summary["at_risk_nodes"] > 0:
                    at_risk += 1
                elif exec_summary["completed_nodes"] > 0:
                    completed += 1
                else:
                    in_progress += 1

            # ✅ project count
            programme_project_counts[p.id] = total

            # ✅ summary
            programme_summary[p.id] = {
                "total": total,
                "completed": completed,
                "in_progress": in_progress,
                "at_risk": at_risk
            }

    return HTMLResponse(
        jinja_env.get_template("programmes.html").render(
            user=user,
            programmes=programmes,
            project_counts=programme_project_counts,
            programme_summary=programme_summary  # ✅ FIXED
        )
    )


@app.get("/programmes/", response_class=HTMLResponse)
def programmes_ui_slash(request: Request):
    return programmes_ui(request)

@app.post("/programme/delete/{programme_id}")
def delete_programme(programme_id: int, request: Request):
    user = request.session.get("user")
    
    if user.get("role") != "admin":
        return RedirectResponse("/programmes?error=admin_required", status_code=303)
    with get_db_ctx() as db:
        projects = programme_service.get_projects(db, programme_id)

        # ✅ Prevent delete if projects exist
        if projects:
            return HTMLResponse(
                content="""
                <h3>⚠ Cannot Delete Programme</h3>
                <p>This programme has associated projects.</p>
                <p>Please delete projects first before deleting the programme.</p>
                <br>
                <a href="/programmes">⬅ Back to Programmes</a>
                """,
                status_code=400
            )

        p = db.query(Programme).filter(Programme.id == programme_id).first()
        if p:
            db.delete(p)
            db.commit()

    return RedirectResponse("/programmes", status_code=302)

@app.post("/project/delete/{project_id}")
def delete_project(
    project_id: int,
    request: Request,
    programme_id: int = Form(...)
):

    user = request.session.get("user")

    # =========================================
    # ADMIN ONLY
    # =========================================
    if user.get("role") != "admin":

        return RedirectResponse(
            f"/projects/{programme_id}?error=admin_required",
            status_code=303
        )

    with get_db_ctx() as db:

        # =========================================
        # GET PROJECT
        # =========================================
        project = db.query(Project).filter(
            Project.id == project_id
        ).first()

        if not project:

            return RedirectResponse(
                f"/projects/{programme_id}",
                status_code=303
            )

        # =========================================
        # DELETE EXECUTION DATA
        # =========================================
        db.query(TaskExecution).filter(
            TaskExecution.project_id == project_id
        ).delete(synchronize_session=False)

        # =========================================
        # DELETE TASKS
        # =========================================
        db.query(Task).filter(
            Task.project_id == project_id
        ).delete(synchronize_session=False)

        # =========================================
        # DELETE SCOPES
        # =========================================
        db.query(Scope).filter(
            Scope.project_id == project_id
        ).delete(synchronize_session=False)

        # =========================================
        # DELETE PROJECT ASSIGNMENTS
        # =========================================
        db.query(ProjectAssignment).filter(
            ProjectAssignment.project_id == project_id
        ).delete(synchronize_session=False)

        # =========================================
        # DELETE PROJECT
        # =========================================
        db.delete(project)

        db.commit()

    return RedirectResponse(
        f"/projects/{programme_id}?success=project_deleted",
        status_code=303
    )
@app.get("/programme/edit/{programme_id}", response_class=HTMLResponse)
def edit_programme_ui(programme_id: int, request: Request):
    require_login(request)

    with get_db_ctx() as db:
        p = db.query(Programme).filter(Programme.id == programme_id).first()

    return HTMLResponse(
        f"""
        <h3>Edit Programme</h3>
        <form method="post">
            <input name="name" value="{p.name}" required />
            <button type="submit">💾 Save</button>
        </form>
        <br>
        <a href="/programmes">⬅ Back</a>
        """
    )

@app.post("/programme/edit/{programme_id}")
def edit_programme(
    programme_id: int,
    request: Request,
    name: str = Form(...)
):
    user = request.session.get("user")
    
    if user.get("role") != "admin":
        return RedirectResponse("/programmes?error=admin_required", status_code=303)

    with get_db_ctx() as db:
        p = db.query(Programme).filter(Programme.id == programme_id).first()
        if p:
            p.name = name
            db.commit()

    return RedirectResponse("/programmes", status_code=302)

@app.get("/audit-logs", response_class=HTMLResponse)
def audit_logs_ui(request: Request):

    user = require_login(request)

    role = request.session.get("user", {}).get("role", "user")

    # ✅ RESTRICT ACCESS
    if role != "admin":
        return HTMLResponse(
            "<h3>⚠️ Access Denied</h3><p>Only admin can view audit logs.</p>",
            status_code=403
        )

    return HTMLResponse(
        jinja_env.get_template("audit_logs.html").render(
            user=request.session.get("user")
        )
    )

from models import ProjectAssignment, User

@app.post("/project/{project_id}/assign", response_class=RedirectResponse)
def assign_project(
    project_id: int,
    request: Request,
    user_id: int = Form(...),
    programme_id: int = Form(...)   # ✅ ADD THIS
):
    user = require_login(request)

    # ✅ Only admin allowed
    if user["role"] != "admin":
        return RedirectResponse(
            f"/projects/{programme_id}?error=admin_required",
            status_code=303
        )

    with get_db_ctx() as db:
        # ✅ Prevent duplicate assignment
        existing = db.query(ProjectAssignment).filter(
            ProjectAssignment.project_id == project_id,
            ProjectAssignment.user_id == user_id
        ).first()

        if not existing:
            assignment = ProjectAssignment(
                project_id=project_id,
                user_id=user_id
            )
            db.add(assignment)
            db.commit()

    return RedirectResponse(
        f"/projects/{programme_id}",   # ✅ FIXED here
        status_code=303
    )

@app.post("/project/{project_id}/unassign", response_class=RedirectResponse)
def unassign_project(
    project_id: int,
    request: Request,
    user_id: int = Form(...),
    programme_id: int = Form(...)
):
    user = require_login(request)

    # ✅ Only admin allowed
    if user["role"] != "admin":
        return RedirectResponse(
            f"/projects/{programme_id}?error=admin_required",
            status_code=303
        )

    with get_db_ctx() as db:
        db.query(ProjectAssignment).filter(
            ProjectAssignment.project_id == project_id,
            ProjectAssignment.user_id == user_id
        ).delete()

        db.commit()

    return RedirectResponse(
        f"/projects/{programme_id}",
        status_code=303
    )

from fastapi import Form
from fastapi.responses import RedirectResponse
from models import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@app.get("/register", response_class=HTMLResponse)
def register_page():
    return HTMLResponse(
        jinja_env.get_template("register.html").render()
    )

from services.reporting.project_reporting import (get_project_executive_summary)
from services.reporting.matrix_reporting import (get_project_governance_matrix)

from services.reporting.programme_reporting import (get_programme_executive_summary)

@app.get("/project/{project_id}/executive-dashboard")
def project_executive_dashboard(
    project_id: int,
    request: Request,
):
    user = require_login(request)

    with get_db_ctx() as db:
        report = get_project_executive_summary(project_id, db)
        matrix = get_project_governance_matrix(project_id, db)

        # 1. Fetch the project model entity
        project = db.query(Project).filter(Project.id == project_id).first()
        
        # 2. Extract the parent program relationship ID safely
        program_id = project.programme_id if project and hasattr(project, 'programme_id') else 6

        # 🚀 FIX: Move the rendering inside the DB session context block to prevent detached state errors,
        # and pass explicit variables down for your breadcrumbs to map properly.
        return HTMLResponse(
            jinja_env.get_template("project_executive_dashboard.html").render(
                request=request,  # Essential for session layout state
                user={
                    "role": user.get("role", "viewer"),
                    "username": user.get("username", "Manoj Mishra")
                },
                project=project,
                project_id=project_id,
                
                # 🚀 PASS BOTH VARIANTS TO STOP THE "FIELD REQUIRED" ERROR
                program_id=program_id,      
                programme_id=program_id,    # 🔥 This satisfies the missing query parameter validation tracker!
                report=report,
                matrix=matrix
            )
        )

            
# =========================================
# CIRCLE EXECUTIVE DASHBOARD
# =========================================

@app.get("/project/{project_id}/circle/{circle}")

async def circle_executive_dashboard(
    request: Request,
    project_id: int,
    circle: str,
    db: Session = Depends(get_db)
):

    from services.reporting.circle_reporting import (
        get_circle_executive_summary
    )

    report = get_circle_executive_summary(
        project_id,
        circle,
        db
    )

    if not report:

        return HTMLResponse(
            content="Circle report not found",
            status_code=404
        )

    return templates.TemplateResponse(
        request=request,
        name="circle_executive_dashboard.html",
        context={
            "report": report,
            "user": request.session.get("user")
        }
    )


@app.get("/project/{project_id}/executive-dashboard/pdf")
def export_executive_pdf(
    project_id: int,
    request: Request
):

    require_login(request)

    with get_db_ctx() as db:

        project = db.query(Project).filter(
            Project.id == project_id
        ).first()

        report = get_project_executive_summary(
            project_id,
            db
        )

        pdf = generate_executive_pdf(
            project,
            report
        )

    return StreamingResponse(

        iter([pdf]),

        media_type="application/pdf",

        headers={
            "Content-Disposition":
            f"attachment; filename=Executive_Report_Project_{project_id}.pdf"
        }
    )

# =========================================
# PROGRAMME EXECUTIVE DASHBOARD
# =========================================
        
@app.get(
    "/programme/{programme_id}/executive-dashboard",
    response_class=HTMLResponse
)
def programme_executive_dashboard(

    programme_id: int,
    request: Request
):

    user = require_login(request)

    with get_db_ctx() as db:

        report = get_programme_executive_summary(

            programme_id,
            db
        )

    # SAFETY CHECK
    if not report:

        return HTMLResponse(

            "<h2>Programme not found</h2>",

            status_code=404
        )

    return HTMLResponse(

        jinja_env.get_template(
            "programme_executive_dashboard.html"
        ).render(

            user=user,
            report=report
        )
    )
            
@app.get(
    "/programme/{programme_id}/executive-dashboard/pdf"
)
async def programme_dashboard_pdf(
    programme_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    user = require_login(request)
    programme = db.query(Programme).filter(
        Programme.id == programme_id
    ).first()

    if not programme:

        raise HTTPException(
            status_code=404,
            detail="Programme not found"
        )

    report = get_programme_executive_summary(
        programme_id,
        db
    )
    if not report:

        return HTMLResponse(
            "<h2>Programme not found</h2>",
            status_code=404
    )
    html = jinja_env.get_template(
        "programme_dashboard_pdf.html"
    ).render(
    
        user=user,
        report=report
    )

    pdf_buffer = BytesIO()

    pisa.CreatePDF(

        src=html,

        dest=pdf_buffer

    )

    pdf = pdf_buffer.getvalue()

    return Response(

        content=pdf,

        media_type="application/pdf",

        headers={

            "Content-Disposition":
            f"inline; filename=programme_dashboard_{programme_id}.pdf"

        }
    )


# =========================================
# CIRCLE PDF EXPORT
# =========================================

@app.get(
    "/project/{project_id}/circle/{circle}/pdf"
)

async def export_circle_pdf(
    project_id: int,
    circle: str,
    db: Session = Depends(get_db)
):

    from services.reporting.circle_reporting import (
        get_circle_executive_summary
    )

    from services.reporting.circle_pdf_export import (
        generate_circle_pdf
    )

    report = get_circle_executive_summary(
        project_id,
        circle,
        db
    )

    if not report:

        return HTMLResponse(
            content="Circle report not found",
            status_code=404
        )

    pdf = generate_circle_pdf(report)

    return Response(

        content=pdf,

        media_type="application/pdf",

        headers={

            "Content-Disposition":
                f"inline; filename={circle}_dashboard.pdf"
        }
    )

# =========================================================
# FORECAST DASHBOARD
# =========================================================

@app.get("/project/{project_id}/forecast-dashboard")
def forecast_dashboard(project_id: int, request: Request):

    user = require_login(request)

    with get_db_ctx() as db:

        # =====================================================
        # PROJECT VALIDATION
        # =====================================================

        project = db.query(Project).filter(
            Project.id == project_id
        ).first()

        if not project:
            return RedirectResponse("/home", status_code=303)

        # =====================================================
        # ACCESS VALIDATION
        # =====================================================

        if not validate_project_access(db, user, project_id):
            return RedirectResponse(
                "/home?error=not_authorized",
                status_code=303
            )

        # =====================================================
        # GET SCOPES
        # =====================================================

        scopes = db.query(Scope).filter(
            Scope.project_id == project_id
        ).all()

        # =====================================================
        # TASK MASTER MAP
        # =====================================================

        master_tasks = db.query(Task).filter(
            Task.project_id == project_id
        ).all()

        task_duration_map = {
            t.id: (t.duration_days or 0)
            for t in master_tasks
        }

        forecast_data = []

        # =====================================================
        # NODE FORECAST
        # =====================================================

        for scope in scopes:

            # Skip placeholders
            if (
                str(scope.node_id).upper() == "TBD"
                or str(scope.facility_name).upper() == "TBD"
            ):
                continue

            executions = db.query(TaskExecution).filter(
                TaskExecution.scope_id == scope.id
            ).all()

            if not executions:
                continue

            total_tasks = len(executions)

            completed_tasks = len([
                x for x in executions
                if x.status == "Completed"
            ])

            inprogress_tasks = len([
                x for x in executions
                if x.status == "In Progress"
            ])

            pending_tasks = len([
                x for x in executions
                if x.status == "Not Started"
            ])

            # ==========================================
            # IGNORE NODES NOT STARTED
            # ==========================================

            if completed_tasks == 0 and inprogress_tasks == 0:
                continue

            # ==========================================
            # DURATION WEIGHTED PROGRESS
            # ==========================================

            completed_duration = sum(
                task_duration_map.get(x.task_id, 0)
                for x in executions
                if x.status == "Completed"
            )

            total_duration = sum(
                task_duration_map.get(x.task_id, 0)
                for x in executions
            )

            progress = round(
                (completed_duration / total_duration) * 100,
                1
            ) if total_duration else 0

            # ==========================================
            # ACTUAL ELAPSED
            # ==========================================

            actual_elapsed = 0
            planned_elapsed = 0

            for x in executions:

                task_duration = task_duration_map.get(
                    x.task_id,
                    0
                )

                planned_elapsed += task_duration

                if x.actual_start:

                    end_date = (
                        x.actual_finish
                        if x.actual_finish
                        else date.today()
                    )

                    actual_elapsed += max(
                        0,
                        (end_date - x.actual_start).days
                    )

            # ==========================================
            # PERFORMANCE FACTOR
            # ==========================================

            if planned_elapsed > 0:

                performance_factor = (
                    actual_elapsed /
                    planned_elapsed
                )

            else:
                performance_factor = 1

            performance_factor = max(
                1,
                min(round(performance_factor, 2), 3)
            )

            # ==========================================
            # REMAINING WORK
            # ==========================================

            remaining_duration = sum(
                task_duration_map.get(x.task_id, 0)
                for x in executions
                if x.status != "Completed"
            )

            forecast_remaining = round(
                remaining_duration *
                performance_factor
            )

            # ==========================================
            # PREDICTED GO LIVE
            # ==========================================

            predicted_go_live = (
                date.today() +
                timedelta(days=forecast_remaining)
            )

            # ==========================================
            # PLANNED FINISH
            # ==========================================

            planned_finish_dates = [
                x.planned_finish
                for x in executions
                if x.planned_finish
            ]

            planned_finish = (
                max(planned_finish_dates)
                if planned_finish_dates
                else None
            )

            # ==========================================
            # DELAY
            # ==========================================

            forecast_delay = 0

            if planned_finish:

                forecast_delay = max(
                    0,
                    (
                        predicted_go_live -
                        planned_finish
                    ).days
                )

            # ==========================================
            # RISK
            # ==========================================

            if forecast_delay <= 5:
                risk = "Low"

            elif forecast_delay <= 15:
                risk = "Medium"

            else:
                risk = "High"
            # =================================================
            # CONFIDENCE SCORE
            # =================================================
            confidence = 100
            
            confidence -= forecast_delay * 0.5
            
            confidence -= pending_tasks * 0.3
            
            confidence += progress * 0.2
            
            confidence = max(
                20,
                min(100, round(confidence))
            )
            if confidence >= 85:
                confidence_band = "High"
            
            elif confidence >= 60:
                confidence_band = "Medium"
            
            else:
                confidence_band = "Low"
            
            # =================================================
            # DELAY DRIVERS
            # =================================================
            
            delay_drivers = []
            
            for x in executions:
            
                if x.status == "Completed":
                    continue
            
                remaining_days = task_duration_map.get(
                    x.task_id,
                    0
                )
            
                task_name = ""
            
                master_task = next(
                    (
                        t for t in master_tasks
                        if t.id == x.task_id
                    ),
                    None
                )
            
                if master_task:
                    task_name = master_task.name
            
                delay_drivers.append({
                    "task_name": task_name,
                    "remaining_days": remaining_days
                })
            
            # Biggest contributors first
            delay_drivers.sort(
                key=lambda d: d["remaining_days"],
                reverse=True
            )
            
            # Keep Top 5
            delay_drivers = delay_drivers[:5]

            # ==========================================
            # STORE
            # ==========================================

            forecast_data.append({

                "scope_id": scope.id,

                "node_id": scope.node_id,

                "facility_name": scope.facility_name,

                "circle": scope.circle,

                "progress": progress,

                "completed_tasks": completed_tasks,

                "pending_tasks": pending_tasks,

                "inprogress_tasks": inprogress_tasks,

                "performance_factor": performance_factor,

                "forecast_remaining": forecast_remaining,

                "planned_finish": planned_finish,

                "predicted_go_live": predicted_go_live,

                "forecast_delay": forecast_delay,
                
                "risk": risk,
                
                "confidence": confidence,

                "confidence_band": confidence_band,
                
                "delay_drivers": delay_drivers
            })

        # =====================================================
        # SORT
        # =====================================================

        forecast_data.sort(
            key=lambda x: (
                x["forecast_delay"],
                x["progress"]
            ),
            reverse=True
        )

        # =====================================================
        # DEBUG
        # =====================================================
        
        if forecast_data:
            print(
                "Delay Drivers:",
                forecast_data[0]["delay_drivers"]
            )


        # =====================================================
        # PROJECT KPIs
        # =====================================================

        total_nodes = len(forecast_data)

        high_risk = len([
            x for x in forecast_data
            if x["risk"] == "High"
        ])

        medium_risk = len([
            x for x in forecast_data
            if x["risk"] == "Medium"
        ])

        low_risk = len([
            x for x in forecast_data
            if x["risk"] == "Low"
        ])

        critical_nodes = len([
            x for x in forecast_data
            if x["forecast_delay"] > 30
        ])

        avg_delay = round(
            sum(
                x["forecast_delay"]
                for x in forecast_data
            ) / total_nodes,
            1
        ) if total_nodes else 0

        worst_delay = max(
            [x["forecast_delay"] for x in forecast_data],
            default=0
        )

        project_forecast_date = max(
            [x["predicted_go_live"] for x in forecast_data],
            default=None
        )
        
        avg_confidence = round(
            sum(
                x["confidence"]
                for x in forecast_data
            ) / total_nodes,
            1
        ) if total_nodes else 0

        # =====================================================
        # CIRCLE SUMMARY
        # =====================================================

        circle_summary = {}

        for row in forecast_data:

            circle = row["circle"]

            if circle not in circle_summary:

                circle_summary[circle] = {
                    "nodes": 0,
                    "total_delay": 0,
                    "total_progress": 0,
                    "forecast_dates": []
                }

            circle_summary[circle]["nodes"] += 1
            circle_summary[circle]["total_delay"] += row["forecast_delay"]
            circle_summary[circle]["total_progress"] += row["progress"]
            circle_summary[circle]["forecast_dates"].append(row["predicted_go_live"])

        for circle in circle_summary:

            data = circle_summary[circle]

            data["avg_delay"] = round(
                data["total_delay"] / data["nodes"],
                1
            )

            data["avg_progress"] = round(
                data["total_progress"] / data["nodes"],
                1
            )
            
            data["forecast_go_live"] = max(
                data["forecast_dates"]
            )

        circle_summary = dict(
            sorted(
                circle_summary.items(),
                key=lambda x: x[1]["avg_delay"],
                reverse=True
            )
        )

        top_delayed_nodes = forecast_data[:10]
        
        overall_progress = round(
            sum(x["progress"] for x in forecast_data) / total_nodes,
            1
        ) if total_nodes else 0
        # =====================================================
        # RESPONSE
        # =====================================================
        return HTMLResponse(
            jinja_env.get_template(
                "forecast_dashboard.html"
            ).render(
                user=user,
                project=project,
                project_id=project_id,
                programme_id=project.programme_id,
        
                project_forecast_date=project_forecast_date,
        
                total_nodes=total_nodes,
                critical_nodes=critical_nodes,
        
                high_risk=high_risk,
                medium_risk=medium_risk,
                low_risk=low_risk,
        
                average_delay=avg_delay,
                worst_delay=worst_delay,
                
                avg_confidence=avg_confidence,
                overall_progress=overall_progress,
        
                circle_summary=circle_summary,
        
                top_delayed_nodes=top_delayed_nodes,
                
        
                forecast_data=forecast_data
            )
        )


# =========================================
    # CIRCLE DASHBOARD
# =========================================
@app.get("/circle-dashboard")
def circle_dashboard(request: Request):

    user = require_login(request)

    with get_db_ctx() as db:

        scopes = db.query(Scope).all()

        circle_summary = {}
        all_programmes = set()
        all_projects = set()

        for scope in scopes:

            if not scope.circle:
                continue

            if str(scope.circle).upper() == "TBD":
                continue

            circle = scope.circle

            if circle not in circle_summary:

                circle_summary[circle] = {
                    "facilities": set(),
                    "projects": set(),
                    "programmes": set(),
                    "total_nodes": 0,
                    "completed_nodes": 0,
                    "wip_nodes": 0
                }

            circle_summary[circle]["total_nodes"] += 1

            circle_summary[circle]["facilities"].add(
                scope.facility_name
            )

            circle_summary[circle]["projects"].add(
                scope.project_id
            )

            project = db.query(Project).filter(
                Project.id == scope.project_id
            ).first()

            if project:
                circle_summary[circle]["programmes"].add(
                    project.programme_id
                )
                
                all_programmes.add(
                        project.programme_id
                    )
                
                all_projects.add(
                    scope.project_id
                )

            # =====================================
            # NODE PROGRESS
            # =====================================

            total_tasks = db.query(TaskExecution).filter(
                TaskExecution.scope_id == scope.id
            ).count()

            completed_tasks = db.query(TaskExecution).filter(
                TaskExecution.scope_id == scope.id,
                TaskExecution.status == "Completed"
            ).count()

            percent = (
                int((completed_tasks / total_tasks) * 100)
                if total_tasks else 0
            )

            if percent == 100:
                circle_summary[circle]["completed_nodes"] += 1
            else:
                circle_summary[circle]["wip_nodes"] += 1

        # =====================================
        # FINAL DATA
        # =====================================

        circle_data = []

        for circle, data in circle_summary.items():

            progress = round(
                (
                    data["completed_nodes"]
                    / data["total_nodes"]
                ) * 100,
                1
            ) if data["total_nodes"] else 0

            circle_data.append({

                "circle": circle,

                "facilities":
                    len(data["facilities"]),

                "projects":
                    len(data["projects"]),

                "programmes":
                    len(data["programmes"]),

                "total_nodes":
                    data["total_nodes"],

                "completed_nodes":
                    data["completed_nodes"],

                "wip_nodes":
                    data["wip_nodes"],

                "progress":
                    progress
            })
        circle_data.sort(
            key=lambda x: x["circle"]
        )
        
        # =====================================
        # DASHBOARD KPIs
        # =====================================
        
        total_circles = len(circle_data)

        total_facilities = sum(
            row["facilities"]
            for row in circle_data
        )
        
        total_programmes = len(all_programmes)
        
        total_projects = len(all_projects)
        
        total_nodes = sum(
            row["total_nodes"]
            for row in circle_data
        )
        
        completed_nodes = sum(
            row["completed_nodes"]
            for row in circle_data
        )
        
        
        return HTMLResponse(
            jinja_env.get_template(
                "circle_dashboard.html"
            ).render(
                user=user,
        
                circle_data=circle_data,
        
                total_circles=total_circles,
                total_facilities=total_facilities,
                total_programmes=total_programmes,
                total_projects=total_projects,
                total_nodes=total_nodes,
                completed_nodes=completed_nodes
            )
        )

# =====================================
   # CIRCLE Level Detail
# =====================================
                
@app.get("/circle/{circle_name}")
def circle_detail(
    circle_name: str,
    request: Request
):

    user = require_login(request)

    with get_db_ctx() as db:

        scopes = db.query(Scope).filter(
            Scope.circle == circle_name
        ).all()

        facility_summary = {}

        for scope in scopes:

            facility = scope.facility_name

            if not facility:
                continue

            if facility not in facility_summary:

                facility_summary[facility] = {

                    "projects": set(),
                    "nodes": 0,
                    "completed_nodes": 0,
                    "wip_nodes": 0
                }

            facility_summary[facility]["nodes"] += 1

            facility_summary[facility]["projects"].add(
                scope.project_id
            )

            # -----------------------------------
            # Go Live Completion Logic
            # -----------------------------------

            go_live = db.query(
                TaskExecution
            ).join(
                Task,
                TaskExecution.task_id == Task.id
            ).filter(
                TaskExecution.scope_id == scope.id,
                Task.name == "Go Live",
                TaskExecution.status == "Completed"
            ).first()

            if go_live:

                facility_summary[facility][
                    "completed_nodes"
                ] += 1

            else:

                facility_summary[facility][
                    "wip_nodes"
                ] += 1

        facility_data = []

        for facility,data in facility_summary.items():

            progress = round(
                (
                    data["completed_nodes"]
                    / data["nodes"]
                ) * 100,
                1
            ) if data["nodes"] else 0

            facility_data.append({

                "facility": facility,

                "projects": len(
                    data["projects"]
                ),

                "nodes": data["nodes"],

                "completed_nodes":
                    data["completed_nodes"],

                "wip_nodes":
                    data["wip_nodes"],

                "progress":
                    progress
            })

        facility_data.sort(
            key=lambda x: x["progress"]
        )

        return HTMLResponse(
            jinja_env.get_template(
                "circle_detail.html"
            ).render(

                user=user,

                circle_name=circle_name,

                facility_data=facility_data
            )
        )               
# =====================================
   # FACILITY Level Detail
# =====================================
@app.get("/facility/{facility_name}")
def facility_detail(
    facility_name: str,
    request: Request
):

    user = require_login(request)

    with get_db_ctx() as db:

        scopes = db.query(Scope).filter(
            Scope.facility_name == facility_name
        ).all()

        node_data = []

        for scope in scopes:

            total_tasks = db.query(TaskExecution).filter(
                TaskExecution.scope_id == scope.id
            ).count()

            completed_tasks = db.query(TaskExecution).filter(
                TaskExecution.scope_id == scope.id,
                TaskExecution.status == "Completed"
            ).count()

            progress = (
                round(
                    (completed_tasks / total_tasks) * 100,
                    1
                )
                if total_tasks
                else 0
            )

            status = (
                "Completed"
                if progress == 100
                else "WIP"
            )

            project = db.query(Project).filter(
                Project.id == scope.project_id
            ).first()
            

            node_data.append({

                "scope_id": scope.id,

                "node_id": scope.node_id,

                "circle": scope.circle,         
                
                "project_name":
                    project.name if project else "",

                "progress": progress,

                "status": status
            })

        return HTMLResponse(
            jinja_env.get_template(
                "facility_detail.html"
            ).render(
                user=user,
                facility_name=facility_name,
                node_data=node_data
            )
        )               
                
@app.get("/profile", response_class=HTMLResponse)
def profile_ui(request: Request):
    user = require_login(request)
    return jinja_env.get_template("profile.html").render(user=user)