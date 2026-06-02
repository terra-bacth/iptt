# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra
"""

from collections import Counter, defaultdict
from services.reporting.leadership_actions import (
    get_leadership_actions
)

from services.reporting.kpi_engine import (
    get_project_kpis
)

from services.reporting.stage_resolver import (
    get_scope_current_stage
)

from constants.reporting_weights import (
    STAGE_WEIGHTS
)

from models import (
    Scope,
    Task,
    TaskExecution
)

from services.reporting.status_engine import (
    get_health_status,
    get_delay_status
)

def get_project_executive_summary(
    project_id,
    db
):

    # -----------------------------------
    # KPI SUMMARY
    # -----------------------------------

    kpis = get_project_kpis(
        project_id,
        db
    )

    # -----------------------------------
    # ALL PROJECT SCOPES
    # -----------------------------------

    scopes = db.query(Scope).filter(
        Scope.project_id == project_id
    ).all()

    # -----------------------------------
    # STAGE SUMMARY
    # -----------------------------------

    stage_summary = {}

    total_weight = 0

    for scope in scopes:

        stage = get_scope_current_stage(scope)

        # stage counter
        stage_summary[stage] = (
            stage_summary.get(stage, 0) + 1
        )

        # maturity weight
        total_weight += STAGE_WEIGHTS.get(
            stage,
            0
        )

    # -----------------------------------
    # HEALTH %
    # -----------------------------------

    total_scopes = len(scopes)
    
    # -----------------------------------
    # STAGE COMPLETION %
    # -----------------------------------
    
    stage_completion_percent = {}
    
    for stage, count in stage_summary.items():
    
        if total_scopes > 0:
    
            stage_completion_percent[stage] = round(
                (count / total_scopes) * 100
            )
    
        else:
    
            stage_completion_percent[stage] = 0
    
    
    
    health_percent = 0

    if total_scopes > 0:

        max_possible = total_scopes * 100

        health_percent = round(
            (total_weight / max_possible) * 100,
            2
        )

    # -----------------------------------
    # MOST DELAYED STAGE
    # -----------------------------------

    most_delayed_stage = "-"

    if stage_summary:

        most_delayed_stage = min(
            stage_summary,
            key=lambda s: STAGE_WEIGHTS.get(s, 0)
        )

    # -----------------------------------
    # DELAYED EXECUTION ITEMS
    # -----------------------------------

    delayed_execution = db.query(
        TaskExecution
    ).filter(
        TaskExecution.project_id == project_id,
        TaskExecution.delay_days > 0
    ).all()

    delayed_items = []

    for e in delayed_execution:

        # -----------------------------------
        # GET SCOPE
        # -----------------------------------

        scope = db.query(Scope).filter(
            Scope.id == e.scope_id
        ).first()

        # -----------------------------------
        # GET TASK
        # -----------------------------------

        task = db.query(Task).filter(
            Task.id == e.task_id
        ).first()

        delayed_items.append({

            "circle":
                scope.circle if scope else "-",

            "node":
                scope.node_id if scope else "-",

            "scope":
                scope.facility_name if scope else "-",

            "task":
                task.name if task else "-",

            "delay":
                e.delay_days,

            "status":
                e.status,

            "remarks":
                e.delay_reason if e.delay_reason else "-"
        })

    # -----------------------------------
    # SORT BY MAX DELAY
    # -----------------------------------

    delayed_items = sorted(

        delayed_items,

        key=lambda x: x["delay"],

        reverse=True
    )
    
    circle_summary = defaultdict(lambda: {
    
        "nodes": 0,
    
        "live": 0,
    
        "total_weight": 0
    })
    
    for scope in db.query(Scope).filter(
        Scope.project_id == project_id
    ).all():
    
        stage = get_scope_current_stage(scope)
    
        weight = STAGE_WEIGHTS.get(stage, 0)
    
        c = circle_summary[scope.circle]
    
        c["nodes"] += 1
    
        c["total_weight"] += weight
    
        if stage == "Live":
            c["live"] += 1
    
    # -----------------------------------
    # CIRCLE COMPLETION %
    # -----------------------------------
    
    circle_completion = {}
    
    total_live_nodes = 0
    
    for circle, data in circle_summary.items():
    
        completion = 0
    
        if data["nodes"] > 0:
    
            completion = round(
                (data["live"] / data["nodes"]) * 100
            )
    
        circle_completion[circle] = completion
    
        total_live_nodes += data["live"]
    
    # -----------------------------------
    # OVERALL COMPLETION %
    # -----------------------------------
    
    overall_completion = 0
    
    if total_scopes > 0:
    
            overall_completion = round(
            (total_live_nodes / total_scopes) * 100
        )
        
    
    
    # -----------------------------------
    # FINALIZE
    # -----------------------------------
    
    circle_report = []
    
    for circle, data in circle_summary.items():
    
        progress = round(
            (data["live"] / data["nodes"]) * 100
        )
    
        health = round(
            data["total_weight"] / data["nodes"],
            2
        )
    
        status = get_health_status(health)
    
        circle_report.append({
    
            "circle": circle,
    
            "nodes": data["nodes"],
    
            "progress": progress,
    
            "health": health,
    
            "status": status
        })
    
    # SORT
    circle_report = sorted(
        circle_report,
        key=lambda x: x["health"]
    )

    # -----------------------------------
    # TOP RISK NODES
    # -----------------------------------

    top_risk_nodes = []

    scope_risk_map = {}

    for item in delayed_items:

        node = item["node"]

        if node not in scope_risk_map:

            scope_risk_map[node] = {

                "circle": item["circle"],

                "node": item["node"],

                "facility": item["scope"],

                "max_delay": item["delay"],

                "task": item["task"],

                "status": item["status"]
            }

        else:

            if item["delay"] > scope_risk_map[node]["max_delay"]:

                scope_risk_map[node]["max_delay"] = item["delay"]

                scope_risk_map[node]["task"] = item["task"]

                scope_risk_map[node]["status"] = item["status"]

    # -----------------------------------
    # SORT RISK
    # -----------------------------------

    top_risk_nodes = sorted(

        scope_risk_map.values(),

        key=lambda x: x["max_delay"],

        reverse=True

    )[:10]
    

    # -----------------------------------
    # PRIMARY BOTTLENECK TASK
    # -----------------------------------

    bottleneck = "None"

    if delayed_items:

        task_counter = Counter()

        for item in delayed_items:
            task_counter[item["task"]] += 1

        bottleneck = task_counter.most_common(1)[0][0]


    # -----------------------------------
    # EXECUTIVE NARRATIVE
    # -----------------------------------

    dominant_stage = "-"

    if kpis["stage_mix"]:

        dominant_stage = max(
            kpis["stage_mix"],
            key=kpis["stage_mix"].get
        )

    # -----------------------------------
    # HEALTH INTERPRETATION
    # -----------------------------------

    if kpis["health"] >= 80:

        health_comment = (
            "overall execution is healthy"
        )

    elif kpis["health"] >= 50:

        health_comment = (
            "execution requires leadership attention"
        )

    else:

        health_comment = (
            "project execution is at risk"
        )

    # -----------------------------------
    # NARRATIVE
    # -----------------------------------

    executive_summary = f"""

    Project health is {kpis['health']}%.

    Overall progress is {kpis['progress']}%.

    Majority nodes are currently in
    '{dominant_stage}' stage.

    Total delayed execution items are
    {len(delayed_items)}.

    Most delayed stage observed is
    '{bottleneck}'.

    Current assessment indicates that
    {health_comment}.

    """
    
    # -----------------------------------
    # STAGE AGING ANALYSIS
    # -----------------------------------

    stage_aging = defaultdict(list)

    for scope in scopes:

        stage = get_scope_current_stage(scope)

        total_delay = 0

        for e in scope.executions:

            if (
                e.delay_days
                and e.status != "Completed"
            ):
                total_delay += e.delay_days

        stage_aging[stage].append(total_delay)

    stage_aging_summary = []

    for stage, delays in stage_aging.items():

        avg_delay = round(
            sum(delays) / len(delays),
            1
        ) if delays else 0

        max_delay = max(delays) if delays else 0

        # -----------------------------
        # Risk Level
        # -----------------------------

        risk = get_delay_status(avg_delay)

        # ONLY SHOW STAGES WITH REAL DELAY
        
        if avg_delay > 0:
        
            stage_aging_summary.append({
        
                "stage": stage,
        
                "nodes": len(delays),
        
                "avg_delay": avg_delay,
        
                "max_delay": max_delay,
        
                "risk": risk
            })

    # -----------------------------
    # SORT BY WORST DELAY
    # -----------------------------

    stage_aging_summary = sorted(

        stage_aging_summary,

        key=lambda x: x["avg_delay"],

        reverse=True
    )
    # -----------------------------------
    # LEADERSHIP ACTIONS
    # -----------------------------------
    
    leadership_actions = get_leadership_actions(
        project_id,
        db
    )
    
    # -----------------------------------
    # LEADERSHIP KPI SUMMARY
    # -----------------------------------
    
    leadership_summary = {
    
        "total": len(leadership_actions),
    
        "open": len([
            x for x in leadership_actions
            if x["status"] == "Open"
        ]),
    
        "in_progress": len([
            x for x in leadership_actions
            if x["status"] == "In Progress"
        ]),
    
        "closed": len([
            x for x in leadership_actions
            if x["status"] == "Closed"
        ]),
    
        "overdue": len([
            x for x in leadership_actions
            if x["overdue_days"] > 0
        ])
    }
    
    # -----------------------------------
    # LEADERSHIP CHART DATA
    # -----------------------------------
    
    leadership_priority = {
    
        "High": len([
            x for x in leadership_actions
            if x["priority"] == "High"
        ]),
    
        "Medium": len([
            x for x in leadership_actions
            if x["priority"] == "Medium"
        ]),
    
        "Low": len([
            x for x in leadership_actions
            if x["priority"] == "Low"
        ])
    }
    
    leadership_status = {
    
        "Open": len([
            x for x in leadership_actions
            if x["status"] == "Open"
        ]),
    
        "In Progress": len([
            x for x in leadership_actions
            if x["status"] == "In Progress"
        ]),
    
        "Closed": len([
            x for x in leadership_actions
            if x["status"] == "Closed"
        ])
    }
    # -----------------------------------
    # RETURN
    # -----------------------------------

    return {

        "kpis": kpis,

        "health_percent": health_percent,

        "stage_summary": stage_summary,
        
        "stage_completion_percent": stage_completion_percent,

        "most_delayed_stage": most_delayed_stage,

        "bottleneck": bottleneck,

        "delayed_count": len(delayed_items),

        "delayed_items": delayed_items,
        
        "total_nodes": kpis["total_nodes"],
        
        "circle_report": circle_report,
        
        "executive_summary": executive_summary,
        
        "top_risk_nodes": top_risk_nodes,
        
        "stage_aging": stage_aging_summary,
        
        "leadership_actions": leadership_actions,

        "leadership_summary": leadership_summary,
        
        "leadership_priority": leadership_priority,

        "leadership_status": leadership_status,
        
        "circle_completion": circle_completion,

        "overall_completion": overall_completion
        
    }