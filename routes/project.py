# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra
"""

# routes/project.py

import pandas as pd
from auth.dependencies import require_admin
from datetime import datetime
from fastapi import Request
from io import BytesIO
from fastapi.responses import StreamingResponse

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse, FileResponse
from sqlalchemy.orm import Session
from pandas import ExcelWriter

from database import get_db
from models import Project
from schemas import ProjectCreate, ProjectResponse
from services import programme_service

from services.project_plan_service import persist_project_plan
from services.planner_data_adapter import build_scope_df, build_tasks_df
from services.calendar_utils import HOLIDAYS
from services.runbook_scheduler.planner import generate_project_plan

router = APIRouter()


# --------------------------------------------------
# PROJECT APIs
# --------------------------------------------------

@router.post("/", response_model=ProjectResponse)
def add_project(
    data: ProjectCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    # ✅ STRICT ADMIN CHECK
    require_admin(request)

    return programme_service.create_project(
        db,
        data.programme_id,
        data.name,
        data.priority,
        data.status
    )


@router.get("/", response_model=list[ProjectResponse])
def list_projects(
    programme_id: int | None = None,
    db: Session = Depends(get_db)
):
    return programme_service.get_projects(db, programme_id)


# --------------------------------------------------
# SET / UPDATE PROJECT INITIATION DATE
# --------------------------------------------------

@router.post("/{project_id}/initiation-date")
def set_project_initiation_date(
    project_id: int,
    project_start_date: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        kickoff_date = datetime.strptime(
            project_start_date, "%Y-%m-%d"
        ).date()
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD."
        )

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # ✅ LOCK CHECK
    if project.baseline_locked:
        raise HTTPException(
            status_code=400,
            detail="Baseline is locked. Cannot re-baseline after execution start."
        )

    project.project_start_date = kickoff_date
    db.commit()

    scope_df = build_scope_df(db, project_id)
    tasks_df = build_tasks_df(db, project_id)

    if scope_df.empty:
        raise HTTPException(status_code=400, detail="Project scope not defined")
    if tasks_df.empty:
        raise HTTPException(status_code=400, detail="Project tasks not defined")

    persist_project_plan(
        project_id=project_id,
        kickoff_date=kickoff_date,
        scope_df=scope_df,
        tasks_df=tasks_df,
        holidays=HOLIDAYS
    )

    return RedirectResponse(
        f"/projects/{project.programme_id}",
        status_code=303
    )


# --------------------------------------------------
# MATRIX HELPER
# --------------------------------------------------

def generate_day0_matrix_df(
    plan_df: pd.DataFrame,
    tasks_df: pd.DataFrame,
    scope_df: pd.DataFrame
) -> pd.DataFrame:

    scope_meta = scope_df[[
        "scope_id",
        "scope_name",
        "priority",
        "circle",
        "facility_name",
        "num_servers"
    ]].drop_duplicates()

    task_order = (
        tasks_df[["template_task_number", "task_name"]]
        .drop_duplicates()
        .sort_values("template_task_number")
    )

    ordered_task_columns = []
    for _, row in task_order.iterrows():
        ordered_task_columns.append(f"{row['task_name']} (Start)")
        ordered_task_columns.append(f"{row['task_name']} (Finish)")

    start_df = plan_df.copy()
    start_df["Task_Column"] = start_df["task_name"] + " (Start)"
    start_df["Value"] = start_df["Planned Start"]

    finish_df = plan_df.copy()
    finish_df["Task_Column"] = finish_df["task_name"] + " (Finish)"
    finish_df["Value"] = plan_df["Planned Finish"]

    combined = pd.concat([start_df, finish_df], ignore_index=True)

    matrix = combined.pivot_table(
        index="scope_name",
        columns="Task_Column",
        values="Value",
        aggfunc="first"
    )

    existing_task_cols = [c for c in ordered_task_columns if c in matrix.columns]
    matrix = matrix[existing_task_cols].reset_index()

    final_matrix = scope_meta.merge(
        matrix,
        how="left",
        on="scope_name"
    )

    final_columns = [
        "priority",
        "circle",
        "facility_name",
        "num_servers",
        "scope_name",
    ] + existing_task_cols

    return final_matrix[final_columns]


# --------------------------------------------------
# DOWNLOAD DAY-0 PLAN
# --------------------------------------------------

@router.get(
    "/{project_id}/plan/download",
    response_class=StreamingResponse,
    response_model=None
)

def download_day0_plan(
    project_id: int,
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.project_start_date:
        raise HTTPException(
            status_code=400,
            detail="Project initiation date not set"
        )

    scope_df = build_scope_df(db, project_id)
    tasks_df = build_tasks_df(db, project_id)

    if scope_df.empty or tasks_df.empty:
        raise HTTPException(
            status_code=400,
            detail="Scope or tasks not defined"
        )

    plan_df = generate_project_plan(
        kickoff_date=project.project_start_date,
        scope_df=scope_df,
        tasks_df=tasks_df,
        holidays=HOLIDAYS
    )

    matrix_df = generate_day0_matrix_df(plan_df, tasks_df, scope_df)

    output = BytesIO()
    
    with ExcelWriter(output, engine="openpyxl") as writer:
        plan_df.to_excel(
            writer,
            sheet_name="Day0_Normalized",
            index=False
        )
    
        matrix_df.to_excel(
            writer,
            sheet_name="Day0_Matrix",
            index=False
        )
    
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition":
            f'attachment; filename="Day0_Project_{project_id}.xlsx"'
        }
    )