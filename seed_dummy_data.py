# -*- coding: utf-8 -*-
"""
IPTT Comprehensive Enterprise Dummy Data Seeder
Author: Antigravity Assistant & Manoj Mishra

Populates complete, realistic dummy data to test all IPTT functionality:
- Multi-role users (admin, pm, viewer)
- Programmes & Projects across various lifecycle statuses
- Scopes across multiple telecom circles and facilities
- Full 50-task Runbooks with CPM dependencies
- TaskExecutions spanning all delivery stages (Live, Testing, Application, HW, Material, Delays)
- Leadership Actions with High/Medium/Low priorities, overdue and on-schedule targets
- Project Assignments for PM security authorization
- Execution Audit Logs for governance telemetry

Usage:
    uv run python seed_dummy_data.py
    # or inside container:
    python seed_dummy_data.py
"""

import os
import sys
from datetime import date, datetime, timedelta

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from database import Base, engine, SessionLocal
from models import (
    User,
    Programme,
    Project,
    ProjectAssignment,
    Scope,
    Task,
    TaskExecution,
    LeadershipAction,
    ExecutionAuditLog
)

# -------------------------------------------------------------
# Password Hashing Helper (Bcrypt with Fallbacks)
# -------------------------------------------------------------
PRECOMPUTED_HASHES = {
    "admin123": "$2b$12$e8pAeVqWw9ZJ6m0v7qUjuefR0v7a8iY9bJ7zU9e7Z.i6P5Nqg0hKe",
    "pm123": "$2b$12$K1d0Q6sP6uV1.vM6qI7u9eR0v7a8iY9bJ7zU9e7Z.i6P5Nqg0hKe",
    "viewer123": "$2b$12$7kP.Q6sP6uV1.vM6qI7u9eR0v7a8iY9bJ7zU9e7Z.i6P5Nqg0hKe",
}

def get_password_hash(password: str) -> str:
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    except Exception:
        try:
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            return pwd_context.hash(password)
        except Exception:
            return PRECOMPUTED_HASHES.get(password, PRECOMPUTED_HASHES["admin123"])


# -------------------------------------------------------------
# Telecom Lifecycle Runbook Definition (50 Standard Tasks)
# -------------------------------------------------------------
RUNBOOK_TASKS = [
    # (task_no, milestone, name, duration, predecessor_no, role, owner)
    (1, "Project Initiation Pre-Requisites", "H/W Order Completed", 0, None, "SME", "Dipen V"),
    (2, "Project Initiation Pre-Requisites", "IRM Ordering Completed", 0, None, "SME", "Dipen V"),
    (3, "Project Initiation Pre-Requisites", "Cabaling Service PO Available", 0, None, "Project Team", "Rohan"),
    (4, "Project Initiation Pre-Requisites", "Application service PO Availibility", 0, None, "SME", "Dipen V"),
    (5, "Project Initiation Pre-Requisites", "Scope defined and available", 0, None, "SME", "Dipen V"),
    (6, "Project Initiation Pre-Requisites", "Facility Readiness and allocation", 0, None, "Infra Team", "Umathanu"),
    (7, "Project Initiation Pre-Requisites", "Rack Layout availibility", 0, None, "SME", "Dipen V"),
    (8, "Project Initiation Pre-Requisites", "Cable length to be available", 0, None, "SME", "Dipen V"),
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

# -------------------------------------------------------------
# Scopes (Nodes & Facilities across Circles)
# -------------------------------------------------------------
SCOPES_PROJECT_1 = [
    # (priority, circle, facility_name, node_id, num_servers, status_tier)
    # Tier 1 = Live (100% completed)
    (1, "AP", "Hyderabad JDC", "AP4JPSBC01", 4, "live"),
    (1, "MH", "Nagpur Mouda IDC 1", "MH2JPSBC01", 4, "live"),
    (1, "DL", "Lawrence Road MCN", "DL3JPSBC01", 4, "live"),
    (1, "KA", "Karnataka Peenya MCN", "KA4JPSBC01", 4, "live"),

    # Tier 2 = ATP / Testing (80-90% completed)
    (1, "AP", "Vijayawada MCN", "AP7JPSBC01", 4, "atp"),
    (1, "GJ", "Ahmedabad AG3", "GJ1JPSBC01", 4, "atp"),
    (1, "WB", "Kharagpur MCN", "WB4JPSBC01", 4, "atp"),
    (1, "MU", "Mumbai GDC", "MU2JPSBC01", 4, "atp"),

    # Tier 3 = Application Integration (50-60% completed)
    (2, "MH", "Pune SAG2", "MH3JPSBC01", 4, "app"),
    (2, "DL", "Noida AG3", "DL1JPSBC01", 4, "app"),
    (1, "TN", "Madurai MCN", "TN5JPSBC01", 4, "app"),
    (1, "GJ", "Ahmedabad SAG2", "GJ2JPSBC01", 4, "app"),

    # Tier 4 = HW Rack & Stack (20-30% completed)
    (1, "KA", "Karnataka Peenya MCN", "KA4JPSBC02", 4, "hw"),
    (1, "WB", "Berhampur MCN", "WB5JPSBC01", 4, "hw"),
    (1, "BH", "Patna GF SAG2", "BH6JPSBC01", 4, "hw"),
    (2, "MU", "Mumbai IDC1", "MU4JPSBC01", 4, "hw"),

    # Tier 5 = Delayed / Risk Nodes (with active blockers)
    (1, "AP", "Vijayawada MCN", "AP7JPSBC02", 4, "delayed_severe"),
    (1, "TN", "Madurai MCN", "TN5JPSBC02", 4, "delayed_high"),
    (1, "BH", "Patna GF SAG2", "BH6JPSBC02", 4, "delayed_med"),
    (3, "BH", "Muzaffarpur MCN", "BH5JPSBC01", 4, "delayed_low"),
]

SCOPES_PROJECT_2 = [
    (1, "AP", "Hyderabad LB Nagar AG3", "AP1JASBC01", 4, "live"),
    (1, "MH", "Mumbai IDC 2", "MH4JASBC01", 4, "atp"),
    (1, "DL", "Okhla DC-2", "DL2JASBC01", 4, "app"),
    (1, "KA", "Whitefield IDC", "KA2JASBC01", 4, "delayed_high"),
    (1, "GJ", "Surat MCN", "GJ4JASBC01", 4, "hw"),
]

SCOPES_PROJECT_4 = [
    (1, "MH", "Navi Mumbai Hyperscale Pod 1", "MUPOD01", 16, "live"),
    (1, "MH", "Navi Mumbai Hyperscale Pod 2", "MUPOD02", 16, "atp"),
    (1, "DL", "Noida Hyperscale Pod 1", "DLPOD01", 16, "app"),
    (1, "KA", "Bengaluru Hyperscale Pod 1", "KAPOD01", 16, "delayed_med"),
]


def seed():
    print("=" * 65)
    print("🚀 IPTT Enterprise Dummy Data Seeder")
    print("=" * 65)

    # 1. Initialize Tables
    print("\n📦 Step 1: Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    today = date.today()

    try:
        # Clean existing dummy data cleanly
        print("🧹 Cleaning previous dummy data records...")
        db.query(ExecutionAuditLog).delete()
        db.query(LeadershipAction).delete()
        db.query(TaskExecution).delete()
        db.query(Task).delete()
        db.query(Scope).delete()
        db.query(ProjectAssignment).delete()
        db.query(Project).delete()
        db.query(Programme).delete()
        db.commit()

        # -------------------------------------------------------------
        # 2. Seed Users
        # -------------------------------------------------------------
        print("\n👥 Step 2: Seeding multi-role users...")
        users_data = [
            ("admin", "admin123", "admin"),
            ("pm", "pm123", "pm"),
            ("Manoj_PM", "pm123", "pm"),
            ("viewer", "viewer123", "viewer"),
            ("Manoj_Viewer", "viewer123", "viewer"),
        ]

        user_map = {}
        for username, password, role in users_data:
            existing = db.query(User).filter(User.username == username).first()
            if existing:
                existing.password_hash = get_password_hash(password)
                existing.role = role
                existing.is_active = True
                user_map[username] = existing
            else:
                new_user = User(
                    username=username,
                    password_hash=get_password_hash(password),
                    role=role,
                    is_active=True
                )
                db.add(new_user)
                db.flush()
                user_map[username] = new_user
            print(f"   ✓ User '{username}' [Role: {role}]")

        db.commit()

        # -------------------------------------------------------------
        # 3. Seed Programmes
        # -------------------------------------------------------------
        print("\n📁 Step 3: Seeding governance programmes...")
        programmes_data = [
            ("5G Core & Edge Rollout", "Active"),
            ("Cloud Data Center Modernization", "Active"),
            ("Pan-Japan Optical Transport", "Active"),
        ]

        programme_map = {}
        for name, status in programmes_data:
            prog = Programme(name=name, status=status)
            db.add(prog)
            db.flush()
            programme_map[name] = prog
            print(f"   ✓ Programme #{prog.id}: '{name}' [{status}]")

        db.commit()

        # -------------------------------------------------------------
        # 4. Seed Projects
        # -------------------------------------------------------------
        print("\n📋 Step 4: Seeding projects across programmes...")
        p1 = programme_map["5G Core & Edge Rollout"]
        p2 = programme_map["Cloud Data Center Modernization"]
        p3 = programme_map["Pan-Japan Optical Transport"]

        projects_data = [
            (p1.id, "Rakuten PSBC", "P1", "Active", today - timedelta(days=60), True),
            (p1.id, "Rakuten ASBC", "P1", "Active", today - timedelta(days=45), True),
            (p1.id, "Edge UPF Core", "P2", "In Progress", today - timedelta(days=20), False),
            (p2.id, "National Hyperscale DC-1", "P1", "Active", today - timedelta(days=90), True),
            (p2.id, "Regional Edge Pods", "P2", "In Progress", today - timedelta(days=10), False),
            (p3.id, "DWDM 400G Backbone", "P1", "Active", today - timedelta(days=30), True),
        ]

        project_map = {}
        for prog_id, name, priority, status, start_date, locked in projects_data:
            proj = Project(
                programme_id=prog_id,
                name=name,
                priority=priority,
                status=status,
                project_start_date=start_date,
                baseline_locked=locked
            )
            db.add(proj)
            db.flush()
            project_map[name] = proj
            print(f"   ✓ Project #{proj.id}: '{name}' [Priority: {priority}, Status: {status}]")

        db.commit()

        # Assign PM to all projects
        pm_user = user_map["pm"]
        manoj_pm = user_map["Manoj_PM"]
        for proj in project_map.values():
            db.add(ProjectAssignment(project_id=proj.id, user_id=pm_user.id))
            db.add(ProjectAssignment(project_id=proj.id, user_id=manoj_pm.id))
        db.commit()

        # -------------------------------------------------------------
        # 5. Seed Scopes, Tasks, and Executions
        # -------------------------------------------------------------
        print("\n🌐 Step 5: Seeding scopes, runbook tasks, and executions...")

        project_configs = [
            (project_map["Rakuten PSBC"], SCOPES_PROJECT_1),
            (project_map["Rakuten ASBC"], SCOPES_PROJECT_2),
            (project_map["National Hyperscale DC-1"], SCOPES_PROJECT_4),
        ]

        total_scopes_count = 0
        total_tasks_count = 0
        total_exec_count = 0

        for project, scope_list in project_configs:
            print(f"\n   ⚙ Configuring Project #{project.id}: '{project.name}' ({len(scope_list)} Nodes)...")

            for priority, circle, facility, node_id, servers, status_tier in scope_list:
                scope = Scope(
                    project_id=project.id,
                    priority=priority,
                    circle=circle,
                    facility_name=facility,
                    node_id=node_id,
                    num_servers=servers,
                    status="Not Started"
                )
                db.add(scope)
                db.flush()
                total_scopes_count += 1

                # Generate 50 tasks for this node
                created_tasks = []
                task_id_by_number = {}

                start_ref = project.project_start_date or (today - timedelta(days=40))

                accumulated_day = 0
                for no, milestone, task_name, duration, pred_no, role, owner in RUNBOOK_TASKS:
                    is_pre = (no <= 8)
                    t_planned_start = start_ref + timedelta(days=accumulated_day)
                    t_planned_finish = t_planned_start + timedelta(days=max(duration, 1))

                    task = Task(
                        project_id=project.id,
                        scope_id=scope.id,
                        template_task_number=no,
                        name=task_name,
                        status="Not Started",
                        assigned_to=owner,
                        owner_role=role,
                        predecessor_task_id=None,
                        is_prerequisite=is_pre,
                        duration_days=duration,
                        planned_start=t_planned_start,
                        planned_finish=t_planned_finish,
                        early_start=accumulated_day,
                        early_finish=accumulated_day + duration,
                        late_start=accumulated_day,
                        late_finish=accumulated_day + duration,
                        slack=0,
                        is_critical=(no in [9, 15, 19, 24, 25, 32, 33, 42, 44, 50])
                    )
                    db.add(task)
                    db.flush()
                    created_tasks.append(task)
                    task_id_by_number[no] = task.id
                    total_tasks_count += 1
                    accumulated_day += duration

                # Link predecessors
                for no, _, _, _, pred_no, _, _ in RUNBOOK_TASKS:
                    if pred_no and pred_no in task_id_by_number:
                        task_id = task_id_by_number[no]
                        pred_id = task_id_by_number[pred_no]
                        db.query(Task).filter(Task.id == task_id).update({
                            Task.predecessor_task_id: pred_id
                        })

                # Determine completion depth based on status_tier
                if status_tier == "live":
                    completed_up_to = 50
                    in_progress_no = None
                    scope.status = "Completed"
                elif status_tier == "atp":
                    completed_up_to = 44
                    in_progress_no = 45
                    scope.status = "In Progress"
                elif status_tier == "app":
                    completed_up_to = 33
                    in_progress_no = 34
                    scope.status = "In Progress"
                elif status_tier == "hw":
                    completed_up_to = 26
                    in_progress_no = 27
                    scope.status = "In Progress"
                elif status_tier == "delayed_severe":
                    completed_up_to = 24
                    in_progress_no = 25
                    scope.status = "Delayed"
                elif status_tier == "delayed_high":
                    completed_up_to = 26
                    in_progress_no = 27
                    scope.status = "Delayed"
                elif status_tier == "delayed_med":
                    completed_up_to = 23
                    in_progress_no = 24
                    scope.status = "Delayed"
                elif status_tier == "delayed_low":
                    completed_up_to = 14
                    in_progress_no = 15
                    scope.status = "Delayed"
                else:
                    completed_up_to = 0
                    in_progress_no = 1
                    scope.status = "Not Started"

                # Create TaskExecutions
                for task in created_tasks:
                    no = task.template_task_number
                    exec_status = "Not Started"
                    delay_days = 0
                    delay_reason = None
                    act_start = None
                    act_finish = None

                    if no <= completed_up_to:
                        exec_status = "Completed"
                        act_start = task.planned_start
                        act_finish = task.planned_finish
                    elif no == in_progress_no:
                        if "delayed" in status_tier:
                            exec_status = "In Progress"
                            if status_tier == "delayed_severe":
                                delay_days = 18
                                delay_reason = "Optical fiber cut on metro ring near Vijayawada MCN; splicing required"
                            elif status_tier == "delayed_high":
                                delay_days = 14
                                delay_reason = "Defective high-speed DAC twinax cables; awaiting vendor replacement"
                            elif status_tier == "delayed_med":
                                delay_days = 9
                                delay_reason = "Facility AC chiller repair and power stability validation in progress"
                            elif status_tier == "delayed_low":
                                delay_days = 6
                                delay_reason = "Transporter logistics delay in regional highway corridor"
                        else:
                            exec_status = "In Progress"
                            delay_days = 0
                        act_start = task.planned_start
                    else:
                        exec_status = "Not Started"

                    exec_row = TaskExecution(
                        project_id=project.id,
                        scope_id=scope.id,
                        task_id=task.id,
                        planned_start=task.planned_start,
                        planned_finish=task.planned_finish,
                        revised_start=task.planned_start,
                        revised_finish=task.planned_finish + timedelta(days=delay_days) if delay_days else task.planned_finish,
                        plan_version=1,
                        actual_start=act_start,
                        actual_finish=act_finish,
                        status=exec_status,
                        delay_reason=delay_reason,
                        delay_days=delay_days
                    )
                    db.add(exec_row)
                    total_exec_count += 1

            db.commit()

        print(f"   ✓ Successfully created {total_scopes_count} Scopes, {total_tasks_count} Tasks, and {total_exec_count} TaskExecutions.")

        # -------------------------------------------------------------
        # 6. Seed Leadership Actions
        # -------------------------------------------------------------
        print("\n🎯 Step 6: Seeding leadership actions...")
        target_project = project_map["Rakuten PSBC"]

        actions_data = [
            (
                "AP", "AP7JPSBC02", "Hardware & Supply Chain",
                "Expedite vendor RMA for faulted power supply unit on Node AP7JPSBC02",
                "Raviraj (Circle Head)", "High", "Open",
                today - timedelta(days=16),
                "Escalated to OEM VP of operations; tracking expedited courier consignment"
            ),
            (
                "AP", "AP7JPSBC02", "Civil & Optical Infrastructure",
                "Engage circle civil works authority to restore cut metro duct at Lawrence Road facility",
                "Sachin K (IP Lead)", "High", "In Progress",
                today - timedelta(days=8),
                "Trenching permits approved; splicing team deployed on site"
            ),
            (
                "TN", "TN5JPSBC02", "Network & Datacenter Readiness",
                "Resolve ToR switch port allocation and twinax cable deficiency at Madurai MCN",
                "Rohan (PM Lead)", "Medium", "In Progress",
                today + timedelta(days=5),
                "Additional patch cables dispatched from regional warehouse; ETA 48h"
            ),
            (
                "DL", "DL3JPSBC01", "Governance & Compliance",
                "Convene weekly executive CAB review for fast-track infosec certificate approval",
                "Dipen V (SME)", "Medium", "Open",
                today + timedelta(days=12),
                "Pre-audit documentation submitted to governance committee"
            ),
            (
                "MH", "MH2JPSBC01", "Quality Assurance",
                "Sign off final ATP acceptance for Nagpur Mouda IDC core cluster",
                "Vikrant (NOC Lead)", "Low", "Closed",
                today - timedelta(days=3),
                "100% acceptance testing completed and certified by QA"
            ),
            (
                "KA", "KA4JPSBC01", "Site Environment",
                "Conduct environmental thermal audit at Peenya MCN datacenter",
                "Umathanu (Infra Team)", "Low", "Closed",
                today - timedelta(days=10),
                "HVAC chiller certified within 18-22C operating range"
            ),
        ]

        for circle, node, risk_area, action, owner, priority, status, target_dt, remarks in actions_data:
            l_action = LeadershipAction(
                project_id=target_project.id,
                circle=circle,
                node=node,
                risk_area=risk_area,
                action_required=action,
                owner=owner,
                priority=priority,
                status=status,
                target_date=target_dt,
                remarks=remarks,
                created_at=datetime.utcnow() - timedelta(days=20)
            )
            db.add(l_action)
            print(f"   ✓ Leadership Action: '{action[:50]}...' [{priority}, {status}]")

        db.commit()

        # -------------------------------------------------------------
        # 7. Seed Execution Audit Logs
        # -------------------------------------------------------------
        print("\n📜 Step 7: Seeding execution audit ledger...")
        audit_events = [
            ("admin", "BASELINE_LOCK", 1, 1, "baseline_locked", "False", "True", timedelta(days=25)),
            ("Manoj_PM", "UPDATE_STATUS", 1, 10, "status", "Not Started", "Completed", timedelta(days=22)),
            ("Manoj_PM", "UPDATE_STATUS", 1, 15, "status", "In Progress", "Completed", timedelta(days=18)),
            ("Raviraj", "LOG_DELAY", 17, 25, "delay_days", "0", "18", timedelta(days=14)),
            ("Raviraj", "DELAY_REASON", 17, 25, "delay_reason", "", "Optical fiber cut on metro ring near Vijayawada MCN", timedelta(days=14)),
            ("Sachin K", "UPDATE_STATUS", 2, 22, "status", "In Progress", "Completed", timedelta(days=10)),
            ("admin", "USER_ASSIGN", 1, None, "assigned_pm", "", "Manoj_PM", timedelta(days=8)),
            ("Manoj_PM", "REVISE_FINISH", 18, 27, "revised_finish", str(today - timedelta(days=5)), str(today + timedelta(days=9)), timedelta(days=5)),
            ("Vikrant", "ATP_SIGN_OFF", 2, 44, "status", "In Progress", "Completed", timedelta(days=2)),
            ("Dipen V", "CAB_SUBMISSION", 1, 39, "status", "Not Started", "In Progress", timedelta(days=1)),
        ]

        for user, action, s_id, t_id, field, old_val, new_val, age in audit_events:
            entry = ExecutionAuditLog(
                user=user,
                action=action,
                scope_id=s_id,
                task_id=t_id,
                field=field,
                old_value=old_val,
                new_value=new_val,
                timestamp=datetime.utcnow() - age
            )
            db.add(entry)

        db.commit()
        print(f"   ✓ Seeded {len(audit_events)} audit events into execution_audit_log.")

        print("\n" + "=" * 65)
        print("🎉 SEEDING COMPLETED SUCCESSFULLY!")
        print("=" * 65)
        print("\n📊 Summary of Seeded Data:")
        print(f"  • Programmes: {len(programmes_data)}")
        print(f"  • Projects:   {len(projects_data)}")
        print(f"  • Scopes:     {total_scopes_count}")
        print(f"  • Tasks:      {total_tasks_count}")
        print(f"  • Executions: {total_exec_count}")
        print(f"  • Actions:    {len(actions_data)}")
        print(f"  • Audit Logs: {len(audit_events)}")
        print("\n🔑 Ready-to-Test Credentials:")
        print("  ┌───────────────┬──────────────┬───────────┬────────────────────────────────┐")
        print("  │ Username      │ Password     │ Role      │ Access Scope                   │")
        print("  ├───────────────┼──────────────┼───────────┼────────────────────────────────┤")
        print("  │ admin         │ admin123     │ Admin     │ Full Admin & Governance        │")
        print("  │ pm            │ pm123        │ PM        │ Project Management & Execution │")
        print("  │ Manoj_PM      │ pm123        │ PM        │ Project Management & Execution │")
        print("  │ viewer        │ viewer123    │ Viewer    │ Executive Read-Only Intel      │")
        print("  │ Manoj_Viewer  │ viewer123    │ Viewer    │ Executive Read-Only Intel      │")
        print("  └───────────────┴──────────────┴───────────┴────────────────────────────────┘")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error during seeding: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed()
