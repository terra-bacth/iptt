# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra
"""

from models import TaskExecution, Task, Scope
from datetime import date

def get_task_execution_for_scope(db, scope_id: int):
    """
    Returns task execution rows joined with task metadata
    """
    return (
        db.query(TaskExecution, Task)
        .join(Task, TaskExecution.task_id == Task.id)
        .filter(TaskExecution.scope_id == scope_id)
        .order_by(Task.id)
        .all()
    )


def get_scope_by_id(db, scope_id: int):
    return db.query(Scope).filter(Scope.id == scope_id).first()

def complete_task_execution(db, execution_id: int):
    execution = (
        db.query(TaskExecution)
        .filter(TaskExecution.id == execution_id)
        .first()
    )

    if not execution:
        return None

    execution.status = "Completed"
    execution.actual_finish = date.today()

    if not execution.actual_start:
        execution.actual_start = date.today()

    db.commit()
    return execution
def get_scope_progress(db, project_id: int):
    """
    Returns progress details per scope for a project
    """
    results = []

    scopes = db.query(Scope).filter(
        Scope.project_id == project_id
    ).order_by(Scope.priority).all()

    for scope in scopes:
        total = db.query(TaskExecution).filter(
            TaskExecution.scope_id == scope.id
        ).count()

        completed = db.query(TaskExecution).filter(
            TaskExecution.scope_id == scope.id,
            TaskExecution.status == "Completed"
        ).count()

        percent = int((completed / total) * 100) if total > 0 else 0

        if percent == 100:
            status = "Completed"
        elif percent == 0:
            status = "Not Started"
        else:
            status = "In Progress"

        results.append({
            "scope": scope,
            "completed": completed,
            "total": total,
            "percent": percent,
            "status": status
        })

    return results

from services.calendar_utils import working_days_between

def get_task_execution_with_delay(db, scope_id: int):
    """
    Returns task execution with delay analysis for a scope
    """
    rows = (
        db.query(TaskExecution, Task)
        .join(Task, TaskExecution.task_id == Task.id)
        .filter(TaskExecution.scope_id == scope_id)
        .order_by(Task.id)
        .all()
    )

    result = []

    for te, task in rows:
        delay_days = 0
        delay_status = "On Time"

        if te.status == "Completed" and task.planned_finish and te.actual_finish:
            delay_days = working_days_between(
                task.planned_finish, te.actual_finish
            )
            if delay_days > 0:
                delay_status = "Delayed"

        result.append({
            "task": task,
            "execution": te,
            "delay_days": delay_days,
            "delay_status": delay_status
        })

    return result

from services.calendar_utils import working_days_between

def get_scope_delay_summary(db, project_id: int):
    """
    Returns delay summary per scope (node) for a project
    """
    results = []

    scopes = db.query(Scope).filter(
        Scope.project_id == project_id
    ).order_by(Scope.priority).all()

    for scope in scopes:
        rows = (
            db.query(TaskExecution, Task)
            .join(Task, TaskExecution.task_id == Task.id)
            .filter(TaskExecution.scope_id == scope.id)
            .all()
        )

        delayed_tasks = 0
        critical_delays = 0
        total_delay_days = 0

        for te, task in rows:
            if (
                te.status == "Completed"
                and task.planned_finish
                and te.actual_finish
                and te.actual_finish > task.planned_finish
            ):
                delayed_tasks += 1
                delay_days = working_days_between(
                    task.planned_finish,
                    te.actual_finish
                )
                total_delay_days += delay_days

                if task.is_critical:
                    critical_delays += 1

        status = "On Track" if delayed_tasks == 0 else "Delayed"

        results.append({
            "scope": scope,
            "delayed_tasks": delayed_tasks,
            "critical_delays": critical_delays,
            "total_delay_days": total_delay_days,
            "status": status
        })

    return results

from collections import defaultdict

def get_project_delay_heatmap(db, project_id: int):
    """
    Returns delay heatmap data grouped by Circle and Priority
    """
    heatmap = defaultdict(lambda: defaultdict(list))

    # reuse existing detailed delay logic
    scope_delays = get_scope_delay_summary(db, project_id)

    for row in scope_delays:
        scope = row["scope"]
        total_delay = row["total_delay_days"]

        heatmap[scope.circle][scope.priority].append(total_delay)

    # aggregate
    result = {}

    for circle, priorities in heatmap.items():
        result[circle] = {}

        for priority, delays in priorities.items():
            avg_delay = int(sum(delays) / len(delays)) if delays else 0

            if avg_delay == 0:
                risk = "GREEN"
            elif avg_delay <= 2:
                risk = "AMBER"
            else:
                risk = "RED"

            result[circle][priority] = {
                "avg_delay": avg_delay,
                "risk": risk
            }

    return result

def get_project_executive_summary(db, project_id: int):
    scopes = db.query(Scope).filter(
        Scope.project_id == project_id
    ).all()

    total_nodes = len(scopes)

    completed_nodes = 0
    in_progress_nodes = 0
    not_started_nodes = 0
    delayed_nodes = 0
    critical_delay_nodes = 0

    priority_summary = {}
    circle_summary = {}

    for scope in scopes:
        total_tasks = db.query(TaskExecution).filter(
            TaskExecution.scope_id == scope.id
        ).count()

        completed_tasks = db.query(TaskExecution).filter(
            TaskExecution.scope_id == scope.id,
            TaskExecution.status == "Completed"
        ).count()

        percent = int((completed_tasks / total_tasks) * 100) if total_tasks else 0

        if percent == 100:
            completed_nodes += 1
            node_status = "Completed"
        elif percent == 0:
            not_started_nodes += 1
            node_status = "Not Started"
        else:
            in_progress_nodes += 1
            node_status = "In Progress"

        # Detect delays
        rows = (
            db.query(TaskExecution, Task)
            .join(Task, TaskExecution.task_id == Task.id)
            .filter(TaskExecution.scope_id == scope.id)
            .all()
        )

        node_delayed = False
        node_critical_delay = False

        for te, task in rows:
            if (
                te.status == "Completed"
                and task.planned_finish
                and te.actual_finish
                and te.actual_finish > task.planned_finish
            ):
                node_delayed = True
                if task.is_critical:
                    node_critical_delay = True

        if node_delayed:
            delayed_nodes += 1
        if node_critical_delay:
            critical_delay_nodes += 1

        # Priority summary
        priority_summary.setdefault(scope.priority, {"total": 0, "delayed": 0})
        priority_summary[scope.priority]["total"] += 1
        if node_delayed:
            priority_summary[scope.priority]["delayed"] += 1

        # Circle summary
        circle_summary.setdefault(scope.circle, {"total": 0, "delayed": 0})
        circle_summary[scope.circle]["total"] += 1
        if node_delayed:
            circle_summary[scope.circle]["delayed"] += 1

    completion_percent = int((completed_nodes / total_nodes) * 100) if total_nodes else 0

    if critical_delay_nodes > 0:
        health = "RED"
    elif delayed_nodes > 0:
        health = "AMBER"
    else:
        health = "GREEN"

    return {
        "total_nodes": total_nodes,
        "completed_nodes": completed_nodes,
        "in_progress_nodes": in_progress_nodes,
        "not_started_nodes": not_started_nodes,
        "completion_percent": completion_percent,
        "delayed_nodes": delayed_nodes,
        "critical_delay_nodes": critical_delay_nodes,
        "health": health,
        "priority_summary": priority_summary,
        "circle_summary": circle_summary
    }