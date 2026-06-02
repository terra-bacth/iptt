# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra
"""

from collections import Counter

from models import Scope

from services.reporting.stage_resolver import (
    get_scope_current_stage
)

from constants.reporting_weights import (
    STAGE_WEIGHTS
)


def get_project_kpis(project_id, db):

    scopes = db.query(Scope).filter(
        Scope.project_id == project_id
    ).all()

    total_nodes = len(scopes)

    if total_nodes == 0:

        return {

            "total_nodes": 0,
            "live_nodes": 0,
            "health": 0,
            "progress": 0,
            "at_risk_nodes": 0,
            "stage_mix": {},
            "trend": "N/A"
        }

    # -----------------------------------
    # TRACKERS
    # -----------------------------------

    live_nodes = 0

    total_weight = 0

    at_risk_nodes = 0

    stage_counter = Counter()

    # -----------------------------------
    # NODE LOOP
    # -----------------------------------

    for scope in scopes:

        stage = get_scope_current_stage(scope)

        stage_counter[stage] += 1

        weight = STAGE_WEIGHTS.get(stage, 0)

        total_weight += weight

        # -----------------------------------
        # LIVE
        # -----------------------------------

        if stage == "Live":
            live_nodes += 1

        # -----------------------------------
        # AT RISK
        # -----------------------------------

        delayed = False

        for e in scope.executions:

            if e.delay_days and e.delay_days > 7:
                delayed = True
                break

        if delayed:
            at_risk_nodes += 1

    # -----------------------------------
    # HEALTH
    # -----------------------------------

    avg_weight = total_weight / total_nodes

    health = round(avg_weight, 2)

    # -----------------------------------
    # PROGRESS
    # -----------------------------------

    progress = round(
        (live_nodes / total_nodes) * 100,
        2
    )

    # -----------------------------------
    # TREND
    # -----------------------------------

    if health >= 80:
        trend = "▲ On Track"

    elif health >= 50:
        trend = "▶ Stable"

    else:
        trend = "▼ Needs Attention"

    # -----------------------------------
    # RETURN
    # -----------------------------------

    return {

        "total_nodes": total_nodes,

        "live_nodes": live_nodes,

        "health": health,

        "progress": progress,

        "at_risk_nodes": at_risk_nodes,

        "stage_mix": dict(stage_counter),

        "trend": trend,

        "status": trend
    }