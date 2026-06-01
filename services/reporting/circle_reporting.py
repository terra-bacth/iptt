from collections import defaultdict

from models import (
    Scope,
    TaskExecution,
    Task,
    Project
)

from services.reporting.stage_resolver import (
    get_scope_current_stage
)

from constants.reporting_weights import (
    STAGE_WEIGHTS
)

from services.reporting.status_engine import (
    get_health_status
)


def get_circle_executive_summary(
    project_id,
    circle,
    db
):

    # =====================================
    # LOAD PROJECT
    # =====================================

    project = db.query(Project).filter(
        Project.id == project_id
    ).first()

    if not project:
        return None

    # =====================================
    # LOAD SCOPES
    # =====================================

    scopes = db.query(Scope).filter(
        Scope.project_id == project_id,
        Scope.circle == circle
    ).all()

    if not scopes:
        return None

    # =====================================
    # BASIC KPI
    # =====================================

    total_nodes = len(scopes)

    live_nodes = 0

    total_weight = 0

    stage_summary = defaultdict(int)

    node_details = []

    # =====================================
    # PROCESS SCOPES
    # =====================================

    for scope in scopes:

        stage = get_scope_current_stage(scope)

        weight = STAGE_WEIGHTS.get(stage, 0)

        total_weight += weight

        stage_summary[stage] += 1

        if stage == "Live":

            live_nodes += 1

        # ---------------------------------

        total_delay = 0

        for e in scope.executions:

            if (
                e.delay_days
                and e.status != "Completed"
            ):
                total_delay += e.delay_days

        # ---------------------------------

        node_details.append({

            "scope_id": scope.id,
            
            "node": scope.node_id,

            "facility": scope.facility_name,

            "stage": stage,

            "delay": total_delay
        })

    # =====================================
    # HEALTH
    # =====================================

    health = round(
        total_weight / total_nodes,
        2
    )

    # =====================================
    # COMPLETION
    # =====================================

    completion = round(
        (live_nodes / total_nodes) * 100
    )

    # =====================================
    # STATUS
    # =====================================

    status = get_health_status(health)

    # =====================================
    # STAGE %
    # =====================================

    stage_percent = {}

    for stage, count in stage_summary.items():

        stage_percent[stage] = round(
            (count / total_nodes) * 100
        )

    # =====================================
    # DELAYED ITEMS
    # =====================================

    delayed_items = []

    executions = db.query(TaskExecution).filter(
        TaskExecution.project_id == project_id,
        TaskExecution.delay_days > 0
    ).all()

    for e in executions:

        scope = db.query(Scope).filter(
            Scope.id == e.scope_id,
            Scope.circle == circle
        ).first()

        if not scope:
            continue

        task = db.query(Task).filter(
            Task.id == e.task_id
        ).first()

        delayed_items.append({

            "node": scope.node_id,

            "facility": scope.facility_name,

            "task": task.name if task else "-",

            "delay": e.delay_days,

            "remarks": e.delay_reason or "-"
        })

    # =====================================
    # SORT DELAYS
    # =====================================

    delayed_items = sorted(

        delayed_items,

        key=lambda x: x["delay"],

        reverse=True
    )
    
    # =====================================
    # DEPLOYMENT VELOCITY ANALYTICS
    # =====================================
    
    total_delay = sum([
        x["delay"]
        for x in delayed_items
    ])
    
    avg_delay = 0
    
    if delayed_items:
    
        avg_delay = round(
            total_delay / len(delayed_items),
            1
        )
    
    # -------------------------------------
    # VELOCITY STATUS
    # -------------------------------------
    
    velocity = "Healthy"
    
    if completion < 30:
    
        velocity = "Slow"
    
    elif completion < 70:
    
        velocity = "Moderate"
    
    elif completion >= 70:
    
        velocity = "Fast"
    
    # -------------------------------------
    # FORECAST STATUS
    # -------------------------------------
    
    forecast = "On Track"
    
    if avg_delay > 20:
    
        forecast = "High Risk"
    
    elif avg_delay > 10:
    
        forecast = "Needs Attention"
    
    # -----------------------------------
    # EXECUTIVE SUMMARY
    # -----------------------------------
    
    dominant_stage = "-"
    
    if stage_summary:
    
        dominant_stage = max(
            stage_summary,
            key=stage_summary.get
        )
    
    health_comment = "Execution is progressing normally."
    
    if completion < 30:
    
        health_comment = (
            "Execution requires acceleration."
        )
    
    elif completion >= 80:
    
        health_comment = (
            "Execution is nearing completion."
        )
    
    executive_summary = f"""
    
    Circle '{circle}' currently has {total_nodes} deployment nodes with overall completion at {completion}% and {live_nodes} nodes live. Dominant deployment stage is '{dominant_stage}' with total delayed items observed at {len(delayed_items)}. Current assessment indicates that {health_comment} """.strip()

    # =====================================
    # RETURN
    # =====================================

    return {

        "project_id": project.id,

        "project_name": project.name,

        "circle": circle,

        "total_nodes": total_nodes,

        "live_nodes": live_nodes,

        "completion": completion,

        "health": health,
        
        "avg_delay": avg_delay,

        "velocity": velocity,

        "forecast": forecast,

        "status": status,

        "stage_summary": dict(stage_summary),

        "stage_percent": stage_percent,

        "node_details": node_details,
        
        "executive_summary": executive_summary,

        "delayed_items": delayed_items
    }