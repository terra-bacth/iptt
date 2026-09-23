# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra
"""

from pydantic import BaseModel

# -------------------------
# Programme Schemas
# -------------------------
class ProgrammeCreate(BaseModel):
    name: str
    status: str = "Active"


class ProgrammeResponse(BaseModel):
    id: int
    name: str
    status: str

    class Config:
        orm_mode = True


# -------------------------
# Project Schemas
# -------------------------
class ProjectCreate(BaseModel):
    programme_id: int
    name: str
    priority: str
    status: str = "Not Started"


class ProjectResponse(ProjectCreate):
    id: int

    class Config:
        orm_mode = True
        # -------------------------
# Task Schemas
# -------------------------
class TaskCreate(BaseModel):
    project_id: int
    name: str
    assigned_to: str | None = None
    predecessor_task_id: int | None = None
    is_prerequisite: int = 0
    is_project_initiation: int = 0


class TaskResponse(BaseModel):
    id: int
    project_id: int
    name: str
    status: str
    assigned_to: str | None
    predecessor_task_id: int | None
    is_prerequisite: int
    is_project_initiation: int

    class Config:
        orm_mode = True