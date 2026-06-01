# -*- coding: utf-8 -*-
"""
Created on Wed May 13 15:35:54 2026

@author: Manoj5.Mishra
"""

from models import ProjectAssignment

def is_project_assigned(db, project_id: int, user_id: int):
    return db.query(ProjectAssignment).filter(
        ProjectAssignment.project_id == project_id,
        ProjectAssignment.user_id == user_id
    ).first() is not None