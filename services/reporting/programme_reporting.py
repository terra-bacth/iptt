# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra
"""

from collections import defaultdict

from models import (
    Programme,
    Project
)

from services.reporting.project_reporting import (
    get_project_executive_summary
)

from services.reporting.status_engine import (
    get_health_status
)

from services.reporting.reporting_stage_sequence import (
    STAGE_SEQUENCE
)

def get_programme_executive_summary(
    programme_id,
    db
):

    # -----------------------------------
    # LOAD PROGRAMME
    # -----------------------------------

    programme = db.query(Programme).filter(
        Programme.id == programme_id
    ).first()
    
    if not programme:
        return None

    # -----------------------------------
    # LOAD PROJECTS
    # -----------------------------------

    projects = db.query(Project).filter(
        Project.programme_id == programme_id
    ).all()

    # -----------------------------------
    # AGGREGATION VARIABLES
    # -----------------------------------

    project_reports = []

    total_health = 0

    total_progress = 0

    total_delays = 0

    overall_stage_mix = defaultdict(int)

    overall_circle_summary = defaultdict(lambda: {
        "count": 0,
        "health_total": 0
    })

    # -----------------------------------
    # PROJECT LOOP
    # -----------------------------------

    for project in projects:

        report = get_project_executive_summary(
            project.id,
            db
        )

        if not report:
            continue

        # -----------------------------------
        # BASIC KPIs
        # -----------------------------------

        health = report["kpis"]["health"]

        progress = report["kpis"]["progress"]

        delayed = report["delayed_count"]

        total_health += health

        total_progress += progress

        total_delays += delayed

        # -----------------------------------
        # STAGE MIX AGGREGATION
        # -----------------------------------

        for stage, count in report["stage_summary"].items():

            overall_stage_mix[stage] += count

        # -----------------------------------
        # CIRCLE AGGREGATION
        # -----------------------------------

        for c in report.get("circle_report", []):

            circle = c["circle"]

            overall_circle_summary[circle]["count"] += 1

            overall_circle_summary[circle]["health_total"] += c["health"]

        # -----------------------------------
        # PROJECT REPORT
        # -----------------------------------

        project_reports.append({

            "project_id": project.id,

            "project_name": project.name,

            "health": health,

            "progress": progress,

            "delayed_items": delayed,

            "status": get_health_status(health)
        })

    # -----------------------------------
    # PROGRAMME KPI SUMMARY
    # -----------------------------------

    total_projects = len(project_reports)

    avg_health = 0

    avg_progress = 0

    if total_projects > 0:

        avg_health = round(
            total_health / total_projects,
            2
        )

        avg_progress = round(
            total_progress / total_projects,
            2
        )

    # -----------------------------------
    # PROGRAMME STATUS
    # -----------------------------------

    programme_status = get_health_status(
        avg_health
    )

    # -----------------------------------
    # WORST PROJECTS
    # -----------------------------------

    worst_projects = sorted(

        project_reports,

        key=lambda x: x["health"]

    )[:5]

    # -----------------------------------
    # BEST PROJECTS
    # -----------------------------------

    best_projects = sorted(

        project_reports,

        key=lambda x: x["health"],

        reverse=True

    )[:5]

    # -----------------------------------
    # CIRCLE SUMMARY FINALIZATION
    # -----------------------------------

    circle_summary = []

    for circle, data in overall_circle_summary.items():

        avg_circle_health = 0

        if data["count"] > 0:
        
            avg_circle_health = round(
                data["health_total"] / data["count"],
                2
            )

        circle_summary.append({
        
            "circle": circle,
        
            "nodes": data["count"],
        
            "health": avg_circle_health,
        
            "status": get_health_status(
                avg_circle_health
            )
        })

    # -----------------------------------
    # SORT CIRCLES
    # -----------------------------------

    circle_summary = sorted(

        circle_summary,

        key=lambda x: x["health"]
    )
    # -----------------------------------
    # SORTED STAGE MIX
    # -----------------------------------
    
    sorted_stage_mix = {}
    
    for stage in STAGE_SEQUENCE:
    
        if stage in overall_stage_mix:
    
            sorted_stage_mix[stage] = overall_stage_mix[stage]
    
    # Add unknown stages at end
    
    for stage, count in overall_stage_mix.items():
    
        if stage not in sorted_stage_mix:
    
            sorted_stage_mix[stage] = count
    # -----------------------------------
    # DOMINANT STAGE
    # -----------------------------------

    dominant_stage = "-"

    if overall_stage_mix:

        dominant_stage = max(

            overall_stage_mix,

            key=overall_stage_mix.get
        )
    # -----------------------------------
    # EMPTY PROJECT SAFETY
    # -----------------------------------
    
    if total_projects == 0:
    
        executive_summary = (
            f"No active projects found under programme "
            f"'{programme.name}'."
        )
    
    else:
    # -----------------------------------
    # EXECUTIVE SUMMARY
    # -----------------------------------

        executive_summary = f"""
        Programme '{programme.name}' currently manages {total_projects} active projects.
        
        Average programme health is {avg_health}% with overall progress at {avg_progress}%.
        
        Dominant execution stage across programme is '{dominant_stage}'.
        
        Total delayed execution items across projects are {total_delays}.
        
        Current programme assessment is '{programme_status}'.
        """.strip()


        highest_delay_project = None
        
        if project_reports:
        
            highest_delay_project = max(
                project_reports,
                key=lambda x: x["delayed_items"]
            )
        
        worst_circle = None
        
        if circle_summary:
        
            worst_circle = min(
                circle_summary,
                key=lambda x: x["health"]
            )


    # -----------------------------------
    # FINAL RETURN
    # -----------------------------------
    
    return {

        "programme_id": programme.id,

        "programme_name": programme.name,

        "total_projects": total_projects,

        "avg_health": avg_health,

        "avg_progress": avg_progress,

        "total_delays": total_delays,

        "status": programme_status,

        "dominant_stage": dominant_stage,

        "projects": project_reports,

        "worst_projects": worst_projects,

        "best_projects": best_projects,

        "circle_summary": circle_summary,

        "stage_mix": sorted_stage_mix,
        
        "highest_delay_project": highest_delay_project,

"worst_circle": worst_circle,

        "executive_summary": executive_summary
    }