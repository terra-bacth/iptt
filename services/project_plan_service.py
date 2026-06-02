# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra
"""

# services/project_plan_service.py

from services.runbook_scheduler.planner import generate_project_plan
from models import Task, TaskExecution
from database import get_db


def persist_project_plan(
    project_id: int,
    kickoff_date,
    scope_df,
    tasks_df,
    holidays
):
    """
    Generates and persists planned dates for a project.
    Supports re-baseline by clearing old plan first.
    Initializes execution tracking after planning.
    """

    db = next(get_db())

    try:
        # -------------------------------------------------
        # 1. CLEAR EXISTING DAY-0 PLAN (re-baseline support)
        # -------------------------------------------------
        (
            db.query(Task)
            .filter(Task.project_id == project_id)
            .update(
                {
                    Task.planned_start: None,
                    Task.planned_finish: None
                },
                synchronize_session=False
            )
        )
        db.commit()

        # -------------------------------------------------
        # 2. GENERATE NEW DAY-0 PLAN
        # -------------------------------------------------
        plan_df = generate_project_plan(
            kickoff_date=kickoff_date,
            scope_df=scope_df,
            tasks_df=tasks_df,
            holidays=holidays
        )

        # -------------------------------------------------
        # 3. PERSIST PLANNED DATES INTO TASK
        # -------------------------------------------------
        for _, row in plan_df.iterrows():
            task_id = int(row["task_id"])

            task = (
                db.query(Task)
                .filter(Task.project_id == project_id)
                .filter(Task.id == task_id)
                .first()
            )

            if task:
                task.planned_start = row["Planned Start"]
                task.planned_finish = row["Planned Finish"]

        db.commit()

        # -------------------------------------------------
        # 4. RESET EXECUTION ROWS (re-baseline)
        # -------------------------------------------------
        (
            db.query(TaskExecution)
            .filter(TaskExecution.project_id == project_id)
            .delete(synchronize_session=False)
        )
        db.commit()

        # -------------------------------------------------
        # 5. INITIALIZE TASK EXECUTION (baseline snapshot)
        # -------------------------------------------------
        initialize_task_execution(db, project_id)

    finally:
        db.close()


def initialize_task_execution(db, project_id: int):
    """
    Creates one execution row per (scope, task) using Day-0 baseline.
    """

    tasks = (
        db.query(Task)
        .filter(Task.project_id == project_id)
        .all()
    )

    for t in tasks:
        db.add(
            TaskExecution(
                project_id=project_id,
                scope_id=t.scope_id,
                task_id=t.id,
                planned_start=t.planned_start,
                planned_finish=t.planned_finish,
                status="Not Started",
                delay_days=0
            )
        )

    db.commit()