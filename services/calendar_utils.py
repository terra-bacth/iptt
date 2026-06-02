# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra
"""

from datetime import date, timedelta

# -------------------------------------------------
# Holiday Calendar (India / Maharashtra – 2026)
# -------------------------------------------------
HOLIDAYS = {
    date(2026, 5, 1),   # Maharashtra Day
    date(2026, 8, 15),  # Independence Day
    date(2026, 9, 14),  # Ganesh Chaturthi
    date(2026, 10, 2),  # Gandhi Jayanti
    date(2026, 10, 20), # Dussehra
    date(2026, 11, 9),  # Diwali
    date(2026, 11, 10), # Diwali - Bali Pratipada
    date(2026, 11, 11), # Diwali - Bhai Dooj
}

# -------------------------------------------------
# Working-Day Calculator
# -------------------------------------------------
def add_working_days(start_date: date, days: int) -> date:
    """
    Add working days (Mon–Fri) to a given date,
    skipping weekends and configured holidays.
    """
    current = start_date
    added = 0

    while added < days:
        current += timedelta(days=1)

        # Skip weekends
        if current.weekday() >= 5:  # 5=Sat, 6=Sun
            continue

        # Skip holidays
        if current in HOLIDAYS:
            continue

        added += 1

    return current
def working_days_between(start_date, end_date):
    """
    Calculate working days (Mon–Fri, excluding holidays)
    between two dates
    """
    if not start_date or not end_date:
        return 0

    if end_date <= start_date:
        return 0

    days = 0
    current = start_date

    while current < end_date:
        current += timedelta(days=1)

        if current.weekday() >= 5:
            continue
        if current in HOLIDAYS:
            continue

        days += 1

    return days