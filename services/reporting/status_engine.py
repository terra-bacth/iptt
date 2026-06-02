# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra
"""

def get_health_status(score):

    """
    Universal IPTT health classifier
    """

    if score >= 80:
        return "Healthy"

    elif score >= 50:
        return "Attention"

    return "Critical"


def get_delay_status(delay_days):

    """
    Delay severity classifier
    """

    if delay_days >= 15:
        return "Critical"

    elif delay_days >= 7:
        return "Attention"

    return "Healthy"


def get_progress_status(progress):

    """
    Progress maturity classifier
    """

    if progress >= 80:
        return "On Track"

    elif progress >= 50:
        return "At Risk"

    return "Critical"