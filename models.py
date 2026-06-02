# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    UniqueConstraint,
    Date,
    Boolean,
    Text
)
from sqlalchemy.orm import relationship   # ✅ REQUIRED IMPORT
from database import Base


# -------------------------
# Programme Table
# -------------------------
class Programme(Base):
    __tablename__ = "programme"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    status = Column(String, default="Active")

# -------------------------
# Project Table
# -------------------------
class Project(Base):
    __tablename__ = "project"

    id = Column(Integer, primary_key=True, index=True)
    programme_id = Column(Integer, ForeignKey("programme.id"), nullable=False)
    name = Column(String, nullable=False)
    priority = Column(String)
    status = Column(String, default="Not Started")
    project_start_date = Column(Date, nullable=True)
    baseline_locked = Column(Boolean, default=False)


# -------------------------
# Task Table
# -------------------------
class Task(Base):
    __tablename__ = "task"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("project.id"), nullable=False)
    scope_id = Column(Integer, ForeignKey("scope.id"), nullable=False)  # ✅ ADD THIS
    scope = relationship("Scope", back_populates="tasks")
    template_task_number = Column(Integer, nullable=False)
    name = Column(String, nullable=False)

    status = Column(String, default="Not Started")
    

    assigned_to = Column(String)
    owner_role = Column(String)

    predecessor_task_id = Column(Integer, ForeignKey("task.id"), nullable=True)

    is_prerequisite = Column(Boolean, default=False)

    duration_days = Column(Integer, nullable=False, default=1)

    planned_start = Column(Date)
    planned_finish = Column(Date)

    early_start = Column(Integer)
    early_finish = Column(Integer)
    late_start = Column(Integer)
    late_finish = Column(Integer)

    slack = Column(Integer)
    is_critical = Column(Boolean, default=False)


# -------------------------
# Scope Table
# -------------------------
class Scope(Base):
    __tablename__ = "scope"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("project.id"), nullable=False)

    priority = Column(Integer, nullable=False)
    circle = Column(String, nullable=False)
    tasks = relationship("Task", back_populates="scope")
    # ✅ NEW
    executions = relationship("TaskExecution",back_populates="scope")
    facility_name = Column(String, nullable=False)
    node_id = Column(String, nullable=False)

    num_servers = Column(Integer, nullable=False)
    status = Column(String, default="Not Started")

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "node_id",
            name="uq_project_node"
        ),
    )

# -------------------------
# Task Execution (per Scope)
# -------------------------
class TaskExecution(Base):
    __tablename__ = "task_execution"

    id = Column(Integer, primary_key=True, index=True)

    # Identity
    project_id = Column(Integer, ForeignKey("project.id"), nullable=False)
    scope_id = Column(Integer, ForeignKey("scope.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("task.id"), nullable=False)
    # ✅ NEW RELATIONSHIPS
    scope = relationship("Scope",back_populates="executions")
    task = relationship("Task")

    # -------------------------
    # Day-0 baseline snapshot
    # -------------------------
    planned_start = Column(Date, nullable=True)
    planned_finish = Column(Date, nullable=True)
    
    revised_start = Column(Date, nullable=True)
    revised_finish = Column(Date, nullable=True)
    plan_version = Column(Integer, default=1)

    # -------------------------
    # Execution fields (PM updated)
    # -------------------------
    actual_start = Column(Date, nullable=True)
    actual_finish = Column(Date, nullable=True)

    status = Column(String, default="Not Started")
    delay_reason = Column(Text, nullable=True)

    # -------------------------
    # Derived fields
    # -------------------------
    delay_days = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint(
            "scope_id",
            "task_id",
            name="uq_scope_task_execution"
        ),
    )

# -------------------------
# User Table (Authentication)
# -------------------------
class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="viewer")  # future: admin / pm / viewer
    is_active = Column(Boolean, default=True)
    
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

class ExecutionAuditLog(Base):
    __tablename__ = "execution_audit_log"

    id = Column(Integer, primary_key=True, index=True)
    user = Column(String)
    action = Column(String)
    scope_id = Column(Integer)
    task_id = Column(Integer)
    field = Column(String)
    old_value = Column(String)
    new_value = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)


class ProjectAssignment(Base):
    __tablename__ = "project_assignment"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)

class LeadershipAction(Base):

    __tablename__ = "leadership_actions"

    id = Column(Integer, primary_key=True)

    project_id = Column(
        Integer,
        ForeignKey("project.id")
    )

    circle = Column(String)

    node = Column(String)

    risk_area = Column(String)

    action_required = Column(Text)

    owner = Column(String)

    target_date = Column(Date)

    priority = Column(String)

    status = Column(String)

    remarks = Column(Text)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )