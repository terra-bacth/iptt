# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra
"""

from constants.reporting_stage_map import (REPORTING_STAGE_MAP)

from constants.reporting_weights import (STAGE_WEIGHTS)

from models import (TaskExecution)


def get_scope_current_stage(scope):

    """
    Determines highest reporting stage
    reached by this node/scope.
    """

    executions = scope.executions

    if not executions:
        return "Not Started"

    highest_stage = "Not Started"
    highest_weight = 0

    for e in executions:

        # -----------------------------------
        # ONLY TRACK ACTIVE EXECUTION
        # -----------------------------------

        if e.status not in [
            "Completed",
            "In Progress"
        ]:
            continue

        # -----------------------------------
        # TASK RELATION
        # -----------------------------------

        if not e.task:
            continue

        task_name = e.task.name

        # -----------------------------------
        # MAP TO REPORTING STAGE
        # -----------------------------------

        stage = REPORTING_STAGE_MAP.get(task_name)

        if not stage:
            continue

        # -----------------------------------
        # GET WEIGHT
        # -----------------------------------

        weight = STAGE_WEIGHTS.get(stage, 0)

        # -----------------------------------
        # PICK HIGHEST STAGE
        # -----------------------------------

        if weight > highest_weight:

            highest_stage = stage
            highest_weight = weight

    return highest_stage