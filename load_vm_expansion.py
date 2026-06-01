# -*- coding: utf-8 -*-
"""
Created on Fri Apr 17 11:13:38 2026

@author: Manoj5.Mishra
"""

from database import SessionLocal
from services import programme_service
from models import Task

from email_utils import ENABLE_EMAIL
ENABLE_EMAIL = False

# -------------------------------------------------
# VM Expansion Data Definition
# -------------------------------------------------

PROGRAMME_NAME = "VVM Expansion"

PROJECTS = ["Jio PSBC", "Jio ASBC"]

TASKS = [
    # ---- Project Initiation Prerequisites ----
    ("Project Initiation Pre-Requisites", "H/W Order Completed", 0, None, 1, 0, "SME", "Dipen V"),
    ("Project Initiation Pre-Requisites", "IRM Ordering Completed", 0, None, 1, 0, "SME", "Dipen V"),
    ("Project Initiation Pre-Requisites", "Cabaling Service PO Available", 0, None, 1, 0, "Project Team", "Rohan"),
    ("Project Initiation Pre-Requisites", "Application service PO Availability", 0, None, 1, 0, "SME", "Dipen V"),
    ("Project Initiation Pre-Requisites", "Scope defined and available", 0, None, 1, 0, "SME", "Dipen V"),
    ("Project Initiation Pre-Requisites", "Facility Readiness and allocation", 0, None, 1, 0, "Infra Team", "Umathanu"),
    ("Project Initiation Pre-Requisites", "Rack Layout availability", 0, None, 1, 0, "SME", "Dipen V"),
    ("Project Initiation Pre-Requisites", "Cable length to be available", 0, None, 1, 0, "SME", "Dipen V"),

    # ---- Project Initiation ----
    ("Project Kick-Off", "Project Initiation", 1, None, 0, 1, "Project Team", "Rohan"),

    # ---- HW Dispatch ----
    ("HW Dispatch", "H/W at NWH", 2, "Project Initiation", 0, 0, "SME", "Dipen V"),
    ("HW Dispatch", "IRM at NWH", 2, "Project Initiation", 0, 0, "SME", "Dipen V"),
    ("HW Dispatch", "NSIP ID Creation", 1, "IRM at NWH", 0, 0, "SME", "Dipen V"),
    ("HW Dispatch", "DMTO/SO1 Creation for HW", 1, "NSIP ID Creation", 0, 0, "SME", "Dipen V"),
    ("HW Dispatch", "HW @SWH", 5, "DMTO/SO1 Creation for HW", 0, 0, "Project Team", "Rohan"),
    ("HW Dispatch", "HW @Site", 2, "HW @SWH", 0, 0, "Circle", "Raviraj"),

    # ---- Rack & Stack ----
    ("HW Rack & Stack", "HW Rack-stack & Power ON", 2, "HW @Site", 0, 0, "Circle", "Raviraj"),

    # ---- P2P ----
    ("P2P Readiness", "P2P Availability", 3, "Project Initiation", 0, 0, "IP SME", "Shailesh"),
    ("P2P Readiness", "Final P2P Upload", 1, "P2P Availability", 0, 0, "IP SME", "Shailesh"),
    ("P2P Readiness", "P2P Approved", 2, "Final P2P Upload", 0, 0, "IP NPE", "Sachin K"),

    # ---- Go Live ----
    ("Live", "Go Live", 2, "Project Initiation", 0, 0, "NOC", "Vikrant"),
]


# -------------------------------------------------
# Loader Logic
# -------------------------------------------------

def load_data():
    db = SessionLocal()

    print("Creating Programme...")
    programme = programme_service.create_programme(db, PROGRAMME_NAME, "Active")

    for project_name in PROJECTS:
        print(f"\nCreating Project: {project_name}")
        project = programme_service.create_project(
            db, programme.id, project_name, "P1", "Active"
        )

        task_id_map = {}

        print("Creating Tasks...")
        for milestone, name, duration, _, is_pre, is_init, role, owner in TASKS:
            task = programme_service.create_task(
                db=db,
                project_id=project.id,
                name=f"[{milestone}] {name}",
                assigned_to=owner,
                predecessor_task_id=None,
                is_prerequisite=is_pre,
                is_project_initiation=is_init,
            )

            task.duration_days = duration
            task.owner_role = role
            db.commit()

            task_id_map[name] = task.id

        print("Linking Dependencies...")
        for _, name, _, predecessor_name, *_ in TASKS:
            if predecessor_name:
                db.query(Task).filter(
                    Task.id == task_id_map[name]
                ).update({
                    Task.predecessor_task_id: task_id_map[predecessor_name]
                })

        db.commit()
        print(f"Project '{project_name}' loaded successfully")

    db.close()
    print("\n✅ VVM Expansion Programme Fully Loaded")


# -------------------------------------------------
# Run Loader
# -------------------------------------------------
if __name__ == "__main__":
    load_data()