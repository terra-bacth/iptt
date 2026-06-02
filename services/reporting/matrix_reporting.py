# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra
"""

from collections import defaultdict

from models import Scope

from services.reporting.reporting_stage_sequence import (
    STAGE_SEQUENCE
)

from services.reporting.reporting_stage_engine import (
    get_scope_reporting_stage
)

def get_project_governance_matrix(

    project_id,
    db
):

    # -----------------------------------
    # GET PROJECT SCOPES
    # -----------------------------------

    scopes = db.query(Scope).filter(

        Scope.project_id == project_id

    ).all()

    # -----------------------------------
    # MATRIX STRUCTURE
    # -----------------------------------

    matrix = defaultdict(

        lambda: defaultdict(int)
    )

    # -----------------------------------
    # ALL CIRCLES
    # -----------------------------------

    circles = set()

    # -----------------------------------
    # PROCESS EACH NODE
    # -----------------------------------

    for scope in scopes:

        circle = scope.circle or "Unknown"

        stage = get_scope_reporting_stage(
            scope
        )

        # stage x circle
        matrix[stage][circle] += 1

        circles.add(circle)

    # -----------------------------------
    # SORT CIRCLES
    # -----------------------------------

    circles = sorted(list(circles))
    
    # -----------------------------------
    # STAGE ORDERING
    # -----------------------------------
    
    ordered_matrix = {}
    
    for stage in STAGE_SEQUENCE:
    
        if stage in matrix:
    
            ordered_matrix[stage] = matrix[stage]
    # -----------------------------------
    # RETURN
    # -----------------------------------
    # -----------------------------------
    # BUILD FINAL TABLE
    # -----------------------------------

    rows = []

    grand_total = 0

    for stage in ordered_matrix:

        row = {

            "stage": stage
        }

        stage_total = 0

        for circle in circles:

            count = ordered_matrix[stage].get(
                circle,
                0
            )

            row[circle] = count

            stage_total += count

        row["Total"] = stage_total

        grand_total += stage_total

        rows.append(row)

    # -----------------------------------
    # TOTAL ROW
    # -----------------------------------

    total_row = {

        "stage": "Total"
    }

    for circle in circles:

        total_row[circle] = sum(

            row.get(circle, 0)

            for row in rows
        )

    total_row["Total"] = grand_total

    rows.append(total_row)

    return {

        "circles": circles,

        "rows": rows,

        "grand_total": grand_total
    }