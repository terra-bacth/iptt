# -*- coding: utf-8 -*-
"""
VM Expansion – Full Task Loader with CPM
"""

from database import SessionLocal
from services import programme_service
from models import Task
from services.schedule_service import run_cpm

PROGRAMME_NAME = "VM Expansion"
PROJECTS = ["Jio PSBC", "Jio ASBC"]

# task_no, milestone, task_name, duration, FS task_no, role, owner
TASK_TABLE = [
    (1, "Project Initiation Pre-Requistes", "H/W Order Completed", 0, None, "SME", "Dipen V"),
    (2, "Project Initiation Pre-Requistes", "IRM Ordering Completed", 0, None, "SME", "Dipen V"),
    (3, "Project Initiation Pre-Requistes", "Cabaling Service PO Available", 0, None, "Project Team", "Rohan"),
    (4, "Project Initiation Pre-Requistes", "Application service PO Availibility", 0, None, "SME", "Dipen V"),
    (5, "Project Initiation Pre-Requistes", "Scope defined and available", 0, None, "SME", "Dipen V"),
    (6, "Project Initiation Pre-Requistes", "Facility Readiness and allocation", 0, None, "Infra Team", "Umathanu"),
    (7, "Project Initiation Pre-Requistes", "Rack Layout availibility", 0, None, "SME", "Dipen V"),
    (8, "Project Initiation Pre-Requistes", "Cable length to be available", 0, None, "SME", "Dipen V"),
    (9, "Project Kick-Off", "Project Initiation", 1, None, "Project Team", "Rohan"),

    (10, "HW Dispatch & Availibility at site", "H/W at NWH", 2, 9, "SME", "Dipen V"),
    (11, "HW Dispatch & Availibility at site", "IRM at NWH", 2, 9, "SME", "Dipen V"),
    (12, "HW Dispatch & Availibility at site", "NSIP ID Creation", 1, 10, "SME", "Dipen V"),
    (13, "HW Dispatch & Availibility at site", "DMTO/SO1 Creation for HW", 1, 12, "SME", "Dipen V"),
    (14, "HW Dispatch & Availibility at site", "HW @SWH", 5, 13, "Project Team", "Rohan"),
    (15, "HW Dispatch & Availibility at site", "HW @Site", 2, 14, "Circle", "Raviraj"),

    (16, "IRM Dispatch & Availibility at Site", "IRM disptatched", 1, 11, "SME", "Dipen V"),
    (17, "IRM Dispatch & Availibility at Site", "IRM @SWH", 5, 16, "Project Team", "Rohan"),
    (18, "IRM Dispatch & Availibility at Site", "IRM @Site", 2, 17, "Circle", "Raviraj"),

    (19, "HW Rack & Stack", "HW Rack-stack & Power ON", 2, 15, "Circle", "Raviraj"),

    (20, "P2P Readiness", "P2P Availibility", 3, 9, "IP SME", "Shailesh"),
    (21, "P2P Readiness", "Final P2P Upload", 1, 20, "IP SME", "Shailesh"),
    (22, "P2P Readiness", "P2P Approved", 2, 21, "IP NPE", "Sachin K"),

    (23, "IP Readiness", "ToR Site Survey", 1, 22, "IP NPE", "Sachin K"),
    (24, "IP Readiness", "TOR HW I & C", 2, 23, "IP NPE", "Sachin K"),
    (25, "IP Readiness", "IP readiness", 4, 24, "IP NPE", "Sachin K"),
    (26, "IP Readiness", "Ilo Reachability check", 1, 25, "Circle", "Raviraj"),

    (27, "HW Ready for Application I&C", "Server to ToR Cabaling", 2, 26, "Circle", "Raviraj"),
    (28, "HW Ready for Application I&C", "Lebeling", 1, 27, "Circle", "Raviraj"),
    (29, "HW Ready for Application I&C", "HW HOTO Checklist Imp.", 2, 27, "Circle", "Raviraj"),
    (30, "HW Ready for Application I&C", "SO2 Completion", 1, 29, "Circle", "Raviraj"),
    (31, "HW Ready for Application I&C", "HW Handover to Application Team", 1, 29, "Project Team", "Rohan"),

    (32, "OS & Application I&C", "OS Installation", 3, 31, "APP I&C Team", "Rohan"),
    (33, "OS & Application I&C", "Application I & C", 4, 32, "APP I&C Team", "Rohan"),

    (34, "Integration Completion", "SO3 Submission", 1, 33, "SME", "Dipen V"),
    (35, "Integration Completion", "SO4 Completion", 1, 34, "NEID Team", "Vishal"),
    (36, "Integration Completion", "NEID Availibility", 4, 35, "NEID Team", "Vishal"),
    (37, "Integration Completion", "Nw Integration", 5, 33, "SME", "Dipen V"),
    (38, "Integration Completion", "OSS Integration", 5, 36, "SME", "Dipen V"),

    (39, "Infosec Clearance", "Security Clearance", 3, 37, "SME", "Dipen V"),
    (40, "NIT Completion", "NIT Clearance", 2, 37, "SME", "Dipen V"),

    (41, "Testing Completion", "Testing Offered", 1, 40, "SME", "Dipen V"),
    (42, "Testing Completion", "Testing Completion", 4, 41, "Circle", "Raviraj"),

    (43, "ATP Clearance", "ATP Offer", 1, 42, "Circle", "Raviraj"),
    (44, "ATP Clearance", "ATP Acceptance", 2, 43, "NOC", "Vikrant"),

    (45, "IDC HOTO", "IDC - Node Offer", 1, 42, "SME", "Dipen V"),
    (46, "IDC HOTO", "IDC - Node Acceptance", 5, 45, "IDC", "Rajat"),

    (47, "HOTO to NOC", "NOC - Node offer", 1, 43, "SME", "Dipen V"),
    (48, "HOTO to NOC", "NOC - Node Acceptance", 1, 47, "NOC", "Vikrant"),

    (49, "RFS", "Ready for Service", 1, 48, "Project Team", "Rohan"),
    (50, "Live", "Go Live", 2, 49, "NOC", "Vikrant"),
]


def load():
    db = SessionLocal()
    programme = programme_service.create_programme(db, PROGRAMME_NAME, "Active")

    for project_name in PROJECTS:
        project = programme_service.create_project(db, programme.id, project_name, "P1", "Active")

        task_map = {}

        # Create tasks
        for no, milestone, name, duration, _, role, owner in TASK_TABLE:
            task = programme_service.create_task(
                db,
                project.id,
                f"[{milestone}] {name}",
                owner,
                None,
                1 if no <= 8 else 0,
                1 if no == 9 else 0
            )

            task.duration_days = duration
            task.owner_role = role
            db.commit()

            task_map[no] = task.id

        # Link dependencies
        for no, _, _, _, fs, _, _ in TASK_TABLE:
            if fs:
                db.query(Task).filter(Task.id == task_map[no]).update(
                    {Task.predecessor_task_id: task_map[fs]}
                )

        # Run CPM calculation
        run_cpm(db, project.id)

        db.commit()
        print(f"✅ Loaded project {project_name}")

    db.close()
    print("✅ VM Expansion fully loaded")


if __name__ == "__main__":
    load()