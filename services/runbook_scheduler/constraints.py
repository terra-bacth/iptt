# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra
"""

# services/runbook_scheduler/constraints.py

"""
Scheduling constraints for IPTT project planning.

This file defines task-level capacity and grouping rules.
These are ported 1:1 from the original Project Tracker Builder.
"""

# Task-level constraints:
#
# key   : Task Number
# cap_all : Maximum parallel executions allowed globally
# grp   : Resource grouping constraint
#         - "facility"
#         - "circle"
#         - "none"

TASK_CONSTRAINTS = {
    25: {
        "cap_all": 2,
        "grp": "facility",
    },
    32: {
        "cap_all": 4,
        "grp": "circle",
    },
    40: {
        "cap_all": 2,
        "grp": "none",
    },
    41: {
        "cap_all": None,   # Unlimited globally
        "grp": "facility",
    },
}