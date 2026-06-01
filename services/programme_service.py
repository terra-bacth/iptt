# -*- coding: utf-8 -*-
"""
Created on Tue Apr 14 18:51:34 2026
Author: Manoj5.Mishra
"""

from sqlalchemy.orm import Session
from models import Programme, Project, Task
from email_utils import send_email
from services.schedule_service import run_cpm

DEFAULT_NOTIFY_EMAIL = "notify@example.com"

# ---------------------------------
# Programme Logic
# ---------------------------------
def create_programme(db: Session, name: str, status: str):
    programme = Programme(name=name, status=status)
    db.add(programme)
    db.commit()
    db.refresh(programme)
    return programme


def get_programmes(db: Session):
    return db.query(Programme).all()


# ---------------------------------
# Project Logic
# ---------------------------------
def create_project(db: Session, programme_id: int, name: str, priority: str, status: str):
    project = Project(
        programme_id=programme_id,
        name=name,
        priority=priority,
        status=status
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def get_projects(db: Session, programme_id: int | None = None):
    query = db.query(Project)
    if programme_id:
        query = query.filter(Project.programme_id == programme_id)
    return query.all()


# ---------------------------------
# Task & Workflow Logic
# ---------------------------------
def all_prerequisites_completed(db: Session, project_id: int) -> bool:
    prereqs = db.query(Task).filter(
        Task.project_id == project_id,
        Task.is_prerequisite == True
    ).all()

    if not prereqs:
        return False

    return all(t.status == "Completed" for t in prereqs)


def create_task(
    db: Session,
    project_id: int,
    name: str,
    duration_days: int,
    assigned_to: str | None,
    owner_role: str | None,
    predecessor_task_id: int | None,
    is_prerequisite: bool
):
    """
    Create a new task.
    Pre-Requisite tasks must complete before project initiation date.
    """

    task = Task(
        project_id=project_id,
        name=name,
        duration_days=duration_days,
        assigned_to=assigned_to,
        owner_role=owner_role,
        predecessor_task_id=predecessor_task_id,
        is_prerequisite=is_prerequisite,
        status="Active"
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    send_email(
        DEFAULT_NOTIFY_EMAIL,
        "New Task Created",
        f"Task '{task.name}' has been created and is ACTIVE."
    )

    return task


def complete_task_and_activate_next(db: Session, task_id: int):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return None

    # ✅ Mark task completed
    task.status = "Completed"
    db.commit()

    send_email(
        DEFAULT_NOTIFY_EMAIL,
        "Task Completed",
        f"Task '{task.name}' has been completed."
    )

    # ✅ Activate dependent tasks
    dependent_tasks = db.query(Task).filter(
        Task.predecessor_task_id == task.id
    ).all()

    for t in dependent_tasks:
        if t.status != "Completed":
            t.status = "Active"
            send_email(
                DEFAULT_NOTIFY_EMAIL,
                "New Task Activated",
                f"Task '{t.name}' is now ACTIVE."
            )

    # ✅ Recompute CPM after task completion
    run_cpm(db, task.project_id)

    db.commit()
    return task


def get_tasks(db: Session, project_id: int):
    return db.query(Task).filter(Task.project_id == project_id).all()