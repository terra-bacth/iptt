# -*- coding: utf-8 -*-
"""
Created on Mon Apr 27 11:05:37 2026

@author: Manoj5.Mishra
"""

import pandas as pd
from models import Scope, Task

def build_scope_df(db, project_id: int) -> pd.DataFrame:
    scopes = (
        db.query(Scope)
        .filter(Scope.project_id == project_id)
        .all()
    )

    data = []

    for s in scopes:
        data.append({
            "scope_id": s.id,
            "scope_name": s.node_id,        # ✅ used everywhere else
            "priority": s.priority,
            "circle": s.circle,
            "facility_name": s.facility_name,
            "num_servers": s.num_servers,
        })

    df = pd.DataFrame(data)

    # ✅ SAFETY CHECK (keep temporarily)
    print("DEBUG scope_df columns:", df.columns.tolist())

    return df



def build_tasks_df(db, project_id: int) -> pd.DataFrame:
    tasks = (
        db.query(Task)
        .join(Scope, Task.scope_id == Scope.id)
        .filter(Scope.project_id == project_id)
        .all()
    )

    data = []

    for t in tasks:
        duration = (
            (t.planned_finish - t.planned_start).days + 1
            if t.planned_start and t.planned_finish
            else t.duration_days
        )

        data.append({
            "task_id": t.id,
            "template_task_number": t.template_task_number,
            "task_name": t.name,
            "scope_id": t.scope_id,

            # ✅ REQUIRED FOR NEW CONSTRAINTS
            "facility": t.scope.facility_name,   # or correct column
            "circle": t.scope.circle,             # or correct column

            "duration_days": duration,
            "predecessor_task_id": t.predecessor_task_id,
            "is_prerequisite": t.is_prerequisite,
        })

    return pd.DataFrame(data)