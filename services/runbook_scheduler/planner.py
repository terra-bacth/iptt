# services/runbook_scheduler/planner.py

from datetime import date
import pandas as pd
from collections import defaultdict
from services.calendar_utils import add_working_days


# -------------------------------------------------
# Utility helpers
# -------------------------------------------------

def next_working_day(d: date) -> date:
    return add_working_days(d, 1)


def get_last_n_working_days(end_date: date, n: int):
    days = []
    current = end_date
    while len(days) < n:
        days.append(current)
        current = add_working_days(current, -1)
    return days[::-1]


def get_edp(
    kickoff_date: date,
    predecessor_finish: date | None,
    duration: int
) -> date:
    base = max(predecessor_finish, kickoff_date) if predecessor_finish else kickoff_date
    if duration <= 0:
        return base
    return add_working_days(base, duration - 1)


# -------------------------------------------------
# Capacity rules (declarative)
# -------------------------------------------------

TASK_CAPACITY_RULES = {
    13: {"max_per_day": 10},   # DMTO / SO1
    16: {"max_per_day": 5},    # IRM dispatched
    20: {"max_per_day": 5},    # P2P Availability
    40: {"max_per_day": 2},    # NIT Clearance
}


# -------------------------------------------------
# MAIN PLANNER
# -------------------------------------------------

def generate_project_plan(
    kickoff_date: date,
    scope_df: pd.DataFrame,
    tasks_df: pd.DataFrame,
    holidays: set[date],
) -> pd.DataFrame:
    """
    CPM‑correct, scope‑aware, capacity‑aware planner.
    Implements constraints 4, 5, and 7.
    """

    REQUIRED_TASK_COLS = {
        "task_id",
        "template_task_number",
        "task_name",
        "scope_id",
        "duration_days",
        "predecessor_task_id",
        "is_prerequisite",
        "facility",
        "circle",
    }

    missing = REQUIRED_TASK_COLS - set(tasks_df.columns)
    if missing:
        raise ValueError(f"tasks_df missing required columns: {missing}")

    plan_rows = []

    # -------------------------------------------------
    # Project-level trackers
    # -------------------------------------------------

    # Simple per-day caps (tasks 13, 16, 20, 40)
    capacity_usage = defaultdict(lambda: defaultdict(int))

    # Rolling facility usage for Task 25
    ip_facility_usage = defaultdict(set)  # date -> set(facilities)

    # Concurrent pools
    os_pool_overall = defaultdict(int)            # date -> count (Task 32 + 33)
    os_pool_circle = defaultdict(lambda: defaultdict(int))   # date -> circle -> count

    test_pool_circle = defaultdict(lambda: defaultdict(int)) # date -> circle -> count

    # Dependency tracker
    completed_by_template = defaultdict(dict)  # scope_id -> template_id -> finish_date

    # -------------------------------------------------
    # Iterate scopes (nodes)
    # -------------------------------------------------

    for _, scope in scope_df.iterrows():
        scope_id = scope["scope_id"]
        scope_name = scope["scope_name"]

        scoped_tasks = (
            tasks_df[tasks_df["scope_id"] == scope_id]
            .sort_values("template_task_number")
            .reset_index(drop=True)
        )

        if scoped_tasks.empty:
            continue

        for _, task in scoped_tasks.iterrows():
            template_id = int(task["template_task_number"])
            predecessor = task["predecessor_task_id"]
            duration = int(task["duration_days"])
            is_pre = bool(task["is_prerequisite"])
            facility = task["facility"]
            circle = task["circle"]

            # -------------------------------------------------
            # 1. Pre-init gate tasks
            # -------------------------------------------------
            if is_pre:
                planned_start = kickoff_date
                planned_finish = kickoff_date
                completed_by_template[scope_id][template_id] = planned_finish

                plan_rows.append({
                    "scope_id": scope_id,
                    "scope_name": scope_name,
                    "task_id": int(task["task_id"]),
                    "task_name": task["task_name"],
                    "Planned Start": planned_start,
                    "Planned Finish": planned_finish
                })
                continue

            # -------------------------------------------------
            # 2. Dependency resolution
            # -------------------------------------------------
            if pd.notna(predecessor) and int(predecessor) in completed_by_template[scope_id]:
                pred_finish = completed_by_template[scope_id][int(predecessor)]
            else:
                pred_finish = None

            candidate_start = get_edp(kickoff_date, pred_finish, duration)

            # -------------------------------------------------
            # 3A. Simple per-day caps (13, 16, 20, 40)
            # -------------------------------------------------
            if template_id in TASK_CAPACITY_RULES:
                max_pd = TASK_CAPACITY_RULES[template_id]["max_per_day"]
                while capacity_usage[template_id][candidate_start] >= max_pd:
                    candidate_start = next_working_day(candidate_start)
                capacity_usage[template_id][candidate_start] += 1

            # -------------------------------------------------
            # 3B. Constraint 4 — IP Readiness (Task 25)
            # ≤ 2 facilities in rolling 2 working days
            # -------------------------------------------------
            if template_id == 25:
                while True:
                    window = get_last_n_working_days(candidate_start, 2)
                    used_facilities = set()
                    for d in window:
                        used_facilities |= ip_facility_usage[d]

                    if facility in used_facilities or len(used_facilities) < 2:
                        break
                    candidate_start = next_working_day(candidate_start)

                ip_facility_usage[candidate_start].add(facility)

            # -------------------------------------------------
            # 3C. Constraint 5 — OS Installation (32 + 33)
            # ≤ 3 concurrent overall, ≤ 1 per circle
            # -------------------------------------------------
            if template_id in (32, 33):
                while (
                    os_pool_overall[candidate_start] >= 3
                    or os_pool_circle[candidate_start][circle] >= 1
                ):
                    candidate_start = next_working_day(candidate_start)

                os_pool_overall[candidate_start] += 1
                os_pool_circle[candidate_start][circle] += 1

            # -------------------------------------------------
            # 3D. Constraint 7 — Testing Completion (41 + 42)
            # ≤ 1 node per circle concurrently
            # -------------------------------------------------
            if template_id in (41, 42):
                while test_pool_circle[candidate_start][circle] >= 1:
                    candidate_start = next_working_day(candidate_start)

                test_pool_circle[candidate_start][circle] += 1

            # -------------------------------------------------
            # 4. Finalize planned dates
            # -------------------------------------------------
            planned_start = candidate_start
            planned_finish = (
                add_working_days(planned_start, duration - 1)
                if duration > 0 else planned_start
            )

            completed_by_template[scope_id][template_id] = planned_finish

            plan_rows.append({
                "scope_id": scope_id,
                "scope_name": scope_name,
                "task_id": int(task["task_id"]),
                "task_name": task["task_name"],
                "Planned Start": planned_start,
                "Planned Finish": planned_finish
            })

    return pd.DataFrame(plan_rows)