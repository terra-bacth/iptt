# -*- coding: utf-8 -*-
"""
Created on Fri Apr 17 12:42:47 2026

@author: Manoj5.Mishra
"""

from datetime import date
from models import Task
from services.calendar_utils import add_working_days

# ✅ Define project start date (later can be dynamic)
PROJECT_START_DATE = date(2026, 5, 1)

def run_cpm(db, project_id: int):
    tasks = db.query(Task)\
        .filter(Task.project_id == project_id)\
        .order_by(Task.id)\
        .all()

    if not tasks:
        return

    # -----------------------------
    # Forward Pass (ES / EF)
    # -----------------------------
    for task in tasks:
        if not task.predecessor_task_id:
            task.early_start = 0
        else:
            pred = next(
                t for t in tasks
                if t.id == task.predecessor_task_id
            )
            task.early_start = pred.early_finish or 0

        task.early_finish = task.early_start + (task.duration_days or 0)

    project_finish = max(t.early_finish for t in tasks)

    # -----------------------------
    # Backward Pass (LS / LF)
    # -----------------------------
    for task in reversed(tasks):
        successors = [
            t for t in tasks
            if t.predecessor_task_id == task.id
        ]

        if not successors:
            task.late_finish = project_finish
        else:
            task.late_finish = min(
                s.late_start for s in successors
                if s.late_start is not None
            )

        task.late_start = task.late_finish - (task.duration_days or 0)

    # -----------------------------
    # Slack & Critical Path
    # -----------------------------
    for task in tasks:
        task.slack = task.late_start - task.early_start
        task.is_critical = (task.slack == 0)

        # -----------------------------
        # Real Calendar Dates
        # -----------------------------
        task.planned_start = add_working_days(
            PROJECT_START_DATE,
            task.early_start
        )

        task.planned_finish = add_working_days(
            PROJECT_START_DATE,
            task.early_finish
        )

    db.commit()