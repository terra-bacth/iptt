# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra
"""

# -*- coding: utf-8 -*-
"""
TaskExecution Loader – Jio PSBC
"""

from database import SessionLocal
from models import Project, Task, Scope, TaskExecution


def load_task_execution():
    db = SessionLocal()

    # Get project
    project = db.query(Project).filter(
        Project.name == "Jio PSBC"
    ).first()

    if not project:
        print("❌ Project Jio PSBC not found")
        return

    tasks = db.query(Task).filter(
        Task.project_id == project.id
    ).all()

    scopes = db.query(Scope).filter(
        Scope.project_id == project.id
    ).all()

    if not tasks or not scopes:
        print("❌ Tasks or Scope missing")
        return

    count = 0

    for scope in scopes:
        for task in tasks:
            execution = TaskExecution(
                task_id=task.id,
                scope_id=scope.id,
                status="Not Started"
            )
            db.add(execution)
            count += 1

    db.commit()
    db.close()

    print(f"✅ Created {count} TaskExecution rows for Jio PSBC")


if __name__ == "__main__":
    load_task_execution()