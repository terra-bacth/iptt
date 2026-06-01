from constants.reporting_stage_map import (
    REPORTING_STAGE_MAP
)

from services.reporting.stage_resolver import (
    get_scope_current_stage
)


def get_scope_reporting_stage(scope):

    # -----------------------------------
    # CURRENT EXECUTION STAGE
    # -----------------------------------

    current_stage = get_scope_current_stage(scope)

    # -----------------------------------
    # MAP TO GOVERNANCE STAGE
    # -----------------------------------

    return REPORTING_STAGE_MAP.get(

        current_stage,

        current_stage
    )