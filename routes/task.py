# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra
"""

# -*- coding: utf-8 -*-
"""
Task routes – Enterprise‑grade implementation
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
import pandas as pd

from database import get_db
from schemas import TaskCreate, TaskResponse
from models import Task, Project, Scope
from services import programme_service
from contextlib import contextmanager

router = APIRouter()


# ---------------- DB CONTEXT ----------------
@contextmanager
def get_db_ctx():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


# ====================================================
# MANUAL TASK CREATE
# ====================================================
@router.post("/", response_model=TaskResponse)
def add_task(data: TaskCreate, db: Session = Depends(get_db)):
    return programme_service.create_task(
        db,
        data.project_id,
        data.name,
        data.assigned_to,
        data.predecessor_task_id,
        data.is_prerequisite,
        data.is_project_initiation
    )


# ====================================================
# VIEW TASKS
# ====================================================
@router.get("/{project_id}", response_model=list[TaskResponse])
def list_tasks(project_id: int, db: Session = Depends(get_db)):
    return programme_service.get_tasks(db, project_id)


# ====================================================
# COMPLETE TASK
# ====================================================
@router.put("/{task_id}/complete", response_model=TaskResponse)
def complete_task(task_id: int, db: Session = Depends(get_db)):
    task = programme_service.complete_task_and_activate_next(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# ====================================================
# ✅ BULK TASK UPLOAD (REPLACE MODE)
# Applies full task list to every Scope (Node)
# ====================================================
@router.post("/{project_id}/upload")
def upload_task_excel(project_id: int, file: UploadFile = File(...)):

    # ---------------- Validate file ----------------
    if not file.filename.lower().endswith(".xlsx"):
        return RedirectResponse(
            f"/tasks/{project_id}",
            status_code=303
        )

    df = pd.read_excel(file.file)

    required_columns = [
        "Task_Number",
        "Task_Name",
        "Duration_Days",
        "Predecessor_Task_Number",
    ]

    for col in required_columns:
        if col not in df.columns:
            return HTMLResponse(
                f"<h3>Task upload failed: Missing column '{col}'</h3>",
                status_code=400
            )

    # ---------------- Normalize ----------------
    df["Task_Number"] = df["Task_Number"].astype(int)
    df["Task_Name"] = df["Task_Name"].astype(str).str.strip()
    df["Duration_Days"] = df["Duration_Days"].astype(int)
    df["Predecessor_Task_Number"] = (
        df["Predecessor_Task_Number"]
        .fillna(0)
        .astype(int)
    )

    # Deduplicate task template
    df = df.drop_duplicates(subset=["Task_Number"], keep="first")

    with get_db_ctx() as db:

        # ---------------- Fetch all scopes (nodes) ----------------
        scopes = db.query(Scope).filter(
            Scope.project_id == project_id
        ).all()

        if not scopes:
            return HTMLResponse(
                "<h3>Task upload failed: No scopes found for this project.</h3>",
                status_code=400
            )

        tasks_to_insert = []

        # ✅ Cartesian expansion: every task → every scope
        for _, row in df.iterrows():
            for scope in scopes:
                tasks_to_insert.append(
                    Task(
                        project_id=project_id,
                        scope_id=scope.id,          # ✅ REQUIRED
                        template_task_number=row["Task_Number"],  # ✅ STORE IT
                        name=row["Task_Name"],
                        duration_days=row["Duration_Days"],
                        predecessor_task_id=(
                            row["Predecessor_Task_Number"]
                            if row["Predecessor_Task_Number"] > 0 else None
                        ),
                        status="Not Started",
                        is_prerequisite=False
                    )
                )

        # ---------------- Replace‑mode insert ----------------
        try:
            db.query(Task).filter(Task.project_id == project_id).delete()
            db.flush()
            db.bulk_save_objects(tasks_to_insert)
            db.commit()

            project = db.query(Project).filter(
                Project.id == project_id
            ).first()

        except Exception:
            db.rollback()
            raise

    # ---------------- Redirect back to Projects ----------------
    return RedirectResponse(
        f"/projects/{project.programme_id}",
        status_code=303
    )