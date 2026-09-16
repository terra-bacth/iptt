# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra
"""

from models import ProjectAssignment

def is_project_assigned(db, project_id: int, user_id: int):
    return db.query(ProjectAssignment).filter(
        ProjectAssignment.project_id == project_id,
        ProjectAssignment.user_id == user_id
    ).first() is not None