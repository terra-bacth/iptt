# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import RedirectResponse
from fastapi.responses import FileResponse
from io import BytesIO
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import date, datetime
import pandas as pd

from database import get_db
from models import Scope, Task, TaskExecution, Project, ExecutionAuditLog

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter



router = APIRouter(prefix="/api/execution", tags=["Execution"])

# -------------------------------------------------
# API 1: Fetch Execution Grid (Paginated by Scope)
# -------------------------------------------------
@router.get("/project/{project_id}")
def get_execution_grid(
    project_id: int,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    if page < 1 or page_size < 1:
        raise HTTPException(status_code=400, detail="Invalid pagination parameters")

    offset = (page - 1) * page_size

    scopes = (
        db.query(Scope)
        .filter(Scope.project_id == project_id)
        .order_by(Scope.id)
        .offset(offset)
        .limit(page_size)
        .all()
    )

    total_scopes = (
        db.query(Scope)
        .filter(Scope.project_id == project_id)
        .count()
    )

    result = []

    for s in scopes:
        executions = (
            db.query(TaskExecution, Task)
            .join(Task, TaskExecution.task_id == Task.id)
            .filter(
                TaskExecution.scope_id == s.id,
                TaskExecution.project_id == project_id
            )
            .order_by(Task.template_task_number)
            .all()
        )

        tasks_data = []
        for exec_row, task in executions:
            tasks_data.append({
                "task_id": task.id,
                "task_name": task.name,
                "planned_start": exec_row.planned_start,
                "planned_finish": exec_row.planned_finish,
                "actual_start": exec_row.actual_start,
                "actual_finish": exec_row.actual_finish,
                "status": exec_row.status,
                "delay_days": exec_row.delay_days,
                "delay_reason": exec_row.delay_reason
            })

        result.append({
            "scope_id": s.id,
            "scope_name": s.node_id,
            "priority": s.priority,
            "circle": s.circle,
            "facility_name": s.facility_name,
            "num_servers": s.num_servers,
            "tasks": tasks_data
        })

    return {
        "page": page,
        "page_size": page_size,
        "total_scopes": total_scopes,
        "data": result
    }


# -------------------------------------------------
# API 2: Bulk Update Execution
# -------------------------------------------------
# -------------------------------------------------
# API 2: Bulk Update Execution (WITH AUDIT LOGGING)
# -------------------------------------------------
from auth.dependencies import require_pm_or_admin, require_login
from fastapi import Request

from fastapi import Request, HTTPException
from utils.access_control import is_project_assigned
from models import Scope

@router.put("/bulk-update")
def bulk_update_execution(
    updates: list[dict],
    request: Request,
    db: Session = Depends(get_db)
):
    # ✅ AUTH
    require_login(request)
    user_session = require_pm_or_admin(request)

    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    current_user = user_session.get("username")
    user_id = user_session.get("id")

    def parse_date(value):
        if not value:
            return None
        if isinstance(value, date):
            return value
        return datetime.strptime(value, "%Y-%m-%d").date()

    for item in updates:

        exec_row = (
            db.query(TaskExecution)
            .filter(
                TaskExecution.scope_id == item["scope_id"],
                TaskExecution.task_id == item["task_id"]
            )
            .first()
        )

        if not exec_row:
            continue

        # ✅ GET PROJECT FROM SCOPE
        scope = db.query(Scope).filter(Scope.id == exec_row.scope_id).first()
        project_id = scope.project_id if scope else None

        # ✅ ASSIGNMENT CHECK
        if user_session["role"] == "pm":
            if not is_project_assigned(db, project_id, user_id):
                raise HTTPException(
                    status_code=403,
                    detail="Not assigned to this project"
                )

        actual_start = parse_date(item.get("actual_start"))
        actual_finish = parse_date(item.get("actual_finish"))
        user_status = item.get("status")

        task_name = item.get("task_name", f"Task ID {item['task_id']}")

        # ✅ VALIDATIONS
        if actual_finish and not actual_start:
            raise HTTPException(
                status_code=400,
                detail=f"❌ Task '{task_name}': Finish requires Start"
            )

        if user_status == "Completed":
            if not actual_start or not actual_finish:
                raise HTTPException(
                    status_code=400,
                    detail=f"❌ Task '{task_name}': Start & Finish required"
                )

        elif user_status == "In Progress":
            if not actual_start:
                raise HTTPException(
                    status_code=400,
                    detail=f"❌ Task '{task_name}': Start required"
                )

        elif user_status == "Not Started":
            actual_start = None
            actual_finish = None

        # ✅ AUDIT LOG
        def log_change(field, old, new):
            if str(old) != str(new):
                db.add(ExecutionAuditLog(
                    user=current_user,
                    action="UPDATE",
                    scope_id=item["scope_id"],
                    task_id=item["task_id"],
                    field=field,
                    old_value=str(old),
                    new_value=str(new),
                    timestamp=datetime.utcnow()
                ))

        log_change("actual_start", exec_row.actual_start, actual_start)
        log_change("actual_finish", exec_row.actual_finish, actual_finish)
        log_change("status", exec_row.status, user_status)
        log_change("delay_reason", exec_row.delay_reason, item.get("delay_reason"))

        # ✅ APPLY UPDATE
        exec_row.actual_start = actual_start
        exec_row.actual_finish = actual_finish
        
        # ✅ ✅ BASELINE LOCK LOGIC (ADD THIS)
        if actual_start:
            project = db.query(Project).filter(Project.id == project_id).first()
        
            if project and not project.baseline_locked:
                project.baseline_locked = True

        if user_status:
            exec_row.status = user_status
        else:
            if exec_row.actual_finish:
                exec_row.status = "Completed"
            elif exec_row.actual_start:
                exec_row.status = "In Progress"
            else:
                exec_row.status = "Not Started"

        # ✅ SAFETY CORRECTION
        if exec_row.status == "Completed" and not exec_row.actual_finish:
            exec_row.status = "In Progress"

        # ✅ DELAY CALCULATION
        # ✅ Use revised if exists, else fallback to original plan
        planned_finish = exec_row.revised_finish or exec_row.planned_finish
        
        if exec_row.actual_finish and planned_finish:
            delay = (exec_row.actual_finish - planned_finish).days
            exec_row.delay_days = max(0, delay)
        else:
            exec_row.delay_days = 0

        if "delay_reason" in item:
            exec_row.delay_reason = item.get("delay_reason")

    db.commit()

    return {"message": "✅ Execution updated successfully + Logged"}

# -------------------------------------------------
# Delay Heatmap API
# -------------------------------------------------
@router.get("/project/{project_id}/delay-heatmap")
def get_delay_heatmap(project_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(
            Scope.circle,
            Scope.facility_name,
            TaskExecution.delay_days
        )
        .join(TaskExecution, TaskExecution.scope_id == Scope.id)
        .filter(
            Scope.project_id == project_id,
            TaskExecution.delay_days > 0
        )
        .all()
    )

    by_circle = {}
    by_facility = {}

    for circle, facility, delay in rows:
        by_circle.setdefault(circle, {"delayed_tasks": 0, "total_delay_days": 0})
        by_circle[circle]["delayed_tasks"] += 1
        by_circle[circle]["total_delay_days"] += delay

        by_facility.setdefault(facility, {"delayed_tasks": 0, "total_delay_days": 0})
        by_facility[facility]["delayed_tasks"] += 1
        by_facility[facility]["total_delay_days"] += delay

    return {
        "by_circle": [{"circle": k, **v} for k, v in by_circle.items()],
        "by_facility": [{"facility_name": k, **v} for k, v in by_facility.items()]
    }


# -------------------------------------------------
# Executive Summary (Node-based)
# -------------------------------------------------
@router.get("/project/{project_id}/executive-summary")
def get_executive_summary(project_id: int, db: Session = Depends(get_db)):
    scopes = db.query(Scope).filter(Scope.project_id == project_id).all()

    total_nodes = len(scopes)
    completed_nodes = 0
    in_progress_nodes = 0
    at_risk_nodes = 0
    total_delay_days = 0

    for s in scopes:
        executions = (
            db.query(TaskExecution)
            .filter(TaskExecution.scope_id == s.id)
            .all()
        )

        if not executions:
            continue

        has_delay = False
        has_in_progress = False
        all_completed = True

        for e in executions:
            if e.delay_days and e.delay_days > 0:
                has_delay = True
                total_delay_days += e.delay_days
            if e.status == "In Progress":
                has_in_progress = True
            if e.status != "Completed":
                all_completed = False

        if has_delay:
            at_risk_nodes += 1
        elif all_completed:
            completed_nodes += 1
        elif has_in_progress:
            in_progress_nodes += 1

    overall_progress = (
        round((completed_nodes / total_nodes) * 100, 1)
        if total_nodes > 0 else 0
    )

    heatmap = get_delay_heatmap(project_id, db)

    return {
        "total_nodes": total_nodes,
        "completed_nodes": completed_nodes,
        "in_progress_nodes": in_progress_nodes,
        "at_risk_nodes": at_risk_nodes,
        "overall_progress": overall_progress,
        "total_delay_days": total_delay_days,
        "top_circles": heatmap["by_circle"][:3],
        "top_facilities": heatmap["by_facility"][:3],
    }

from services.task_execution_service import get_task_execution_for_scope

@router.get("/scope/{scope_id}")
def get_execution_for_scope(scope_id: int, db=Depends(get_db)):

    scope = db.query(Scope).filter(Scope.id == scope_id).first()

    if not scope:
        return {"error": "Scope not found"}

    rows = get_task_execution_for_scope(db, scope_id)

    tasks = []

    for row in rows:
       execution = row[0]   # TaskExecution
       task = row[1]        # Task ✅ (this is what you need)
    
       tasks.append({
            "task_id": execution.task_id,
            "task_name": task.name if task else "",   # ✅ FIXED
            "task_number": task.template_task_number,   # ✅ ADD
            "planned_start": execution.planned_start,
            "planned_finish": execution.planned_finish,
            
            # ✅ ✅ ADD THESE (CRITICAL FIX)
            "revised_start": execution.revised_start,
            "revised_finish": execution.revised_finish,

            "actual_start": execution.actual_start,
            "actual_finish": execution.actual_finish,
            "status": execution.status,
            "delay_days": execution.delay_days or 0,
            "delay_reason": execution.delay_reason

        })

    return {
        "scope_id": scope.id,
        "scope_name": scope.node_id,
        "circle": scope.circle,
        "facility_name": scope.facility_name,
        "tasks": tasks
    }

@router.get("/scope/{scope_id}/download")
def download_execution(scope_id: int, db=Depends(get_db)):
    from openpyxl.formatting.rule import FormulaRule

    # ✅ Fetch data
    scope = db.query(Scope).filter(Scope.id == scope_id).first()
    if not scope:
        raise HTTPException(status_code=404, detail="Scope not found")

    project = db.query(Project).filter(Project.id == scope.project_id).first()

    project_name = project.name if project else "Project"
    circle = scope.circle or "NA"
    node_id = scope.node_id or f"Node{scope_id}"

    safe_project = project_name.replace(" ", "_")
    safe_circle = circle.replace(" ", "_")
    safe_node = node_id.replace(" ", "_")

    file_name = f"{safe_project}_{safe_circle}_{safe_node}.xlsx"
    

    rows = get_task_execution_for_scope(db, scope_id)

    data = []
    for row in rows:
        execution = row[0]
        task = row[1]

        data.append({
            "Task": task.name if task else "",
            "Planned Start": execution.planned_start,
            "Planned Finish": execution.planned_finish,
            "Actual Start": execution.actual_start,
            "Actual Finish": execution.actual_finish,
            "Status": execution.status,
            "Delay": execution.delay_days,
            "Reason": execution.delay_reason
        })

    df = pd.DataFrame(data)

    # ✅ Create file
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:   

        sheet_name = safe_node[:25]
        df.to_excel(writer, index=False, sheet_name=sheet_name, startrow=3)

        worksheet = writer.sheets[sheet_name]

        # ===============================
        # ✅ HEADER TITLE (TOP SUMMARY)
        # ===============================
        worksheet["A1"] = f"Project: {project_name}"
        worksheet["A2"] = f"Circle: {circle} | Node: {node_id}"

        worksheet["A1"].font = Font(bold=True, size=14)
        worksheet["A2"].font = Font(bold=True)

        # ===============================
        # ✅ HEADER STYLE
        # ===============================
        header_fill = PatternFill(
            start_color="1F4E78", end_color="1F4E78", fill_type="solid"
        )
        header_font = Font(bold=True, color="FFFFFF")
        align_center = Alignment(horizontal="center", vertical="center")

        for col_idx in range(1, len(df.columns) + 1):
            cell = worksheet.cell(row=4, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = align_center

        # ===============================
        # ✅ AUTO COLUMN WIDTH
        # ===============================
        for col_idx, column in enumerate(df.columns, 1):
            max_length = len(column)

            for value in df[column]:
                if value is not None:
                    val = str(value)
                    max_length = max(max_length, len(val))

            width = min(max_length + 2, 40)
            col_letter = worksheet.cell(row=4, column=col_idx).column_letter
            worksheet.column_dimensions[col_letter].width = width

        # ===============================
        # ✅ FREEZE HEADER ROW
        # ===============================
        worksheet.freeze_panes = "A5"

        # ===============================
        # ✅ ALTERNATE ROW COLORS
        # ===============================
        fill_grey = PatternFill(start_color="F2F2F2", fill_type="solid")

        for row_idx in range(5, 5 + len(df)):
            if row_idx % 2 == 0:
                for col_idx in range(1, len(df.columns) + 1):
                    worksheet.cell(row=row_idx, column=col_idx).fill = fill_grey

        # ===============================
        # ✅ TABLE BORDER
        # ===============================
        thin = Side(style="thin")

        for row_cells in worksheet.iter_rows(min_row=4, max_row=4+len(df)):
            for cell in row_cells:
                cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)

        # ===============================
        # ✅ CONDITIONAL COLORING
        # ===============================

        # Red for delayed
        red_fill = PatternFill(start_color="FFC7CE", fill_type="solid")
        worksheet.conditional_formatting.add(
            f"G5:G{4+len(df)}",
            FormulaRule(formula=["$G5>0"], fill=red_fill)
        )

        # Green for completed
        green_fill = PatternFill(start_color="C6EFCE", fill_type="solid")
        worksheet.conditional_formatting.add(
            f"F5:F{4+len(df)}",
            FormulaRule(formula=['$F5="Completed"'], fill=green_fill)
        )

        # Orange for in-progress
        amber_fill = PatternFill(start_color="FFEB9C", fill_type="solid")
        worksheet.conditional_formatting.add(
            f"F5:F{4+len(df)}",
            FormulaRule(formula=['$F5="In Progress"'], fill=amber_fill)
        )

        # ===============================
        # ✅ FILTER ENABLED
        # ===============================
        worksheet.auto_filter.ref = f"A4:H{4+len(df)}"

    output.seek(0)
        
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
                "Content-Disposition":
                f'attachment; filename="{file_name}"'
        }
    )

@router.post("/scope/{scope_id}/upload")
def upload_execution(
    scope_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        

        # ✅ STEP 1: Read raw file first (no header)
        raw_df = pd.read_excel(file.file, header=None)

        header_row_index = None

        # ✅ STEP 2: Detect header row dynamically (search for "Task")
        for i, row in raw_df.iterrows():
            row_values = [str(x).strip().lower() for x in row if pd.notna(x)]

            if "task" in row_values:
                header_row_index = i
                break

        if header_row_index is None:
            raise HTTPException(
                status_code=400,
                detail="❌ Could not find header row (Task column missing in file)"
            )

        # ✅ STEP 3: Reload Excel with correct header
        df = pd.read_excel(file.file, header=header_row_index)

        # ✅ Normalize column names
        df.columns = [str(col).strip().lower() for col in df.columns]

        # ✅ Required columns
        required_columns = [
            "task", "actual start", "actual finish", "status", "reason"
        ]

        for col in required_columns:
            if col not in df.columns:
                raise HTTPException(
                    status_code=400,
                    detail=f"❌ Missing column: {col.title()}"
                )

        # ✅ Build task mapping
        task_map = {}
        rows = get_task_execution_for_scope(db, scope_id)

        for row in rows:
            execution = row[0]
            task = row[1]
            task_map[task.name.strip()] = execution

        # ✅ STEP 4: Process rows
        for _, r in df.iterrows():

            task_name = str(r["task"]).strip()

            if task_name not in task_map:
                continue

            exec_row = task_map[task_name]

            # ✅ Parse dates safely
            actual_start = pd.to_datetime(r["actual start"], errors="coerce")
            actual_finish = pd.to_datetime(r["actual finish"], errors="coerce")

            actual_start = actual_start.date() if pd.notna(actual_start) else None
            actual_finish = actual_finish.date() if pd.notna(actual_finish) else None

            status = str(r["status"]).strip() if pd.notna(r["status"]) else None
            reason = str(r["reason"]).strip() if pd.notna(r["reason"]) else None

            # ========================
            # ✅ VALIDATION RULES
            # ========================

            if status == "Completed":
                if not actual_start and not actual_finish:
                    raise HTTPException(
                        status_code=400,
                        detail=f"❌ Task '{task_name}': Actual Start and Finish required"
                    )
                elif not actual_start:
                    raise HTTPException(
                        status_code=400,
                        detail=f"❌ Task '{task_name}': Actual Start required"
                    )
                elif not actual_finish:
                    raise HTTPException(
                        status_code=400,
                        detail=f"❌ Task '{task_name}': Actual Finish required"
                    )

            elif status == "In Progress":
                if not actual_start:
                    raise HTTPException(
                        status_code=400,
                        detail=f"❌ Task '{task_name}': Actual Start required"
                    )

            elif status == "Not Started":
                actual_start = None
                actual_finish = None

            # ✅ Apply update
            exec_row.actual_start = actual_start
            exec_row.actual_finish = actual_finish
            exec_row.status = status

            # ✅ Delay logic
            if actual_finish and exec_row.planned_finish:
                delay = (actual_finish - exec_row.planned_finish).days
                exec_row.delay_days = max(0, delay)
            else:
                exec_row.delay_days = 0

            exec_row.delay_reason = reason

        db.commit()

        return {"message": "✅ Excel uploaded and execution updated successfully"}

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/log-override")
def log_override(data: dict, db: Session = Depends(get_db)):

    try:
        log = ExecutionAuditLog(
            user=data.get("user"),
            action=data.get("action"),
            scope_id=None,
            task_id=None,
            field="override",
            old_value=None,
            new_value="ON" if data.get("action") == "ENABLE_OVERRIDE" else "OFF",
            timestamp=datetime.utcnow()
        )

        db.add(log)
        db.commit()

        return {"message": "Override logged ✅"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
@router.get("/audit-logs")
def get_audit_logs(
    scope_id: int = None,
    db: Session = Depends(get_db)
):
    logs = db.query(ExecutionAuditLog).order_by(
        ExecutionAuditLog.timestamp.desc()
    )

    if scope_id:
        logs = logs.filter(ExecutionAuditLog.scope_id == scope_id)

    result = []

    for log in logs.limit(200):
        result.append({
            "user": log.user,
            "action": log.action,
            "scope_id": log.scope_id,
            "task_id": log.task_id,
            "field": log.field,
            "old_value": log.old_value,
            "new_value": log.new_value,
            "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S") if log.timestamp else None
        })

    return result

@router.get("/circle/{circle}/download")
def download_circle_execution(circle: str, db: Session = Depends(get_db)):

    import os
    from datetime import datetime
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    scopes = db.query(Scope).filter(Scope.circle == circle).all()

    if not scopes:
        raise HTTPException(status_code=404, detail="No nodes found")

    project = db.query(Project).first()
    project_name = project.name if project else "Project"


    safe_project = project_name.replace(" ", "_")
    safe_circle = circle.replace(" ", "_")
    
    file_name = f"{safe_project}_{safe_circle}_Circle_Plan.xlsx"

    wb = Workbook()
    ws = wb.active
    ws.title = "Circle Plan"

    # ✅ HEADER
    ws["A1"] = f"Project: {project_name}"
    ws["A2"] = f"Circle: {circle}"
    ws["A3"] = f"Downloaded on: {datetime.now().strftime('%d-%b-%Y %H:%M')}"

    ws["A1"].font = Font(size=14, bold=True)
    ws["A2"].font = Font(bold=True)
    ws["A3"].font = Font(italic=True)

    start_row = 5

    # ✅ Basic columns
    ws.cell(row=start_row, column=1, value="Node")
    ws.cell(row=start_row, column=2, value="Facility")

    ws.cell(row=start_row, column=1).font = Font(bold=True)
    ws.cell(row=start_row, column=2).font = Font(bold=True)

    rows = get_task_execution_for_scope(db, scopes[0].id)

    col = 3

    # ✅ Styles
    header_fill = PatternFill(start_color="1F4E78", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)

    task_fill_1 = PatternFill(start_color="E8F1FF", fill_type="solid")
    task_fill_2 = PatternFill(start_color="FDE9D9", fill_type="solid")

    center_align = Alignment(horizontal="center", vertical="center")

    thin = Side(style="thin")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # ✅ Task Header
    for i, r in enumerate(rows, start=1):

        task = r[1]
        task_name = task.name if task else f"Task {i}"

        fill = task_fill_1 if i % 2 == 1 else task_fill_2

        ws.merge_cells(start_row=start_row, start_column=col,
                       end_row=start_row, end_column=col+1)

        cell = ws.cell(row=start_row, column=col, value=task_name)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_align
        cell.border = border

        ws.cell(row=start_row+1, column=col, value="Actual Start")
        ws.cell(row=start_row+1, column=col+1, value="Actual Finish")

        ws.cell(row=start_row+1, column=col).fill = fill
        ws.cell(row=start_row+1, column=col+1).fill = fill

        col += 2

    data_row = start_row + 2

    # ✅ DATA ROWS
    for scope in scopes:

        ws.cell(row=data_row, column=1, value=scope.node_id)
        ws.cell(row=data_row, column=2, value=scope.facility_name)

        ws.cell(row=data_row, column=1).font = Font(bold=True)
        ws.cell(row=data_row, column=2).font = Font(bold=True)

        rows = get_task_execution_for_scope(db, scope.id)

        col = 3

        for idx, r in enumerate(rows, start=1):
            exec_row = r[0]

            fill = task_fill_1 if idx % 2 == 1 else task_fill_2

            ws.cell(row=data_row, column=col, value=exec_row.actual_start)
            ws.cell(row=data_row, column=col+1, value=exec_row.actual_finish)

            ws.cell(row=data_row, column=col).fill = fill
            ws.cell(row=data_row, column=col+1).fill = fill

            col += 2

        data_row += 1

    # ✅ AUTO WIDTH
    for col_idx in range(1, ws.max_column + 1):
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = 18

    # ✅ ✅ STEP 8 FIX — APPLY BORDERS + ALIGNMENT (CRITICAL)
    for row in ws.iter_rows(
        min_row=start_row,
        max_row=data_row,
        min_col=1,
        max_col=ws.max_column
    ):
        for cell in row:
            cell.border = border
            cell.alignment = center_align

    # ✅ ✅ STEP 9 FIX — FREEZE HEADER (PERFECT UX)
    ws.freeze_panes = ws[f"C{start_row + 2}"]

    
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition":
            f'attachment; filename="{file_name}"'
        }
    )


@router.get("/project/{project_id}/download")
def download_project_execution(project_id: int, db: Session = Depends(get_db)):

    import os
    from datetime import datetime
    
    scopes = db.query(Scope).filter(Scope.project_id == project_id).all()

    if not scopes:
        raise HTTPException(status_code=404, detail="No nodes found")

    project = db.query(Project).filter(Project.id == project_id).first()
    project_name = project.name if project else "Project"
    

    file_name = f"{project_name.replace(' ', '_')}_project_plan.xlsx"
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Project Plan"

    # ✅ HEADER
    ws["A1"] = f"Project: {project_name}"
    ws["A2"] = "All Circles"
    ws["A3"] = f"Downloaded on: {datetime.now().strftime('%d-%b-%Y %H:%M')}"

    ws["A1"].font = Font(size=14, bold=True)
    ws["A2"].font = Font(bold=True)

    start_row = 5

    ws.cell(row=start_row, column=1, value="Circle")
    ws.cell(row=start_row, column=2, value="Node")
    ws.cell(row=start_row, column=3, value="Facility")

    ws.cell(row=start_row, column=1).font = Font(bold=True)
    ws.cell(row=start_row, column=2).font = Font(bold=True)
    ws.cell(row=start_row, column=3).font = Font(bold=True)

    # ✅ Styles
    header_fill = PatternFill(start_color="1F4E78", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)

    task_fill_1 = PatternFill(start_color="E8F1FF", fill_type="solid")
    task_fill_2 = PatternFill(start_color="FDE9D9", fill_type="solid")

    center_align = Alignment(horizontal="center", vertical="center")

    thin = Side(style="thin")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # ✅ TASK HEADERS (from first scope)
    rows = get_task_execution_for_scope(db, scopes[0].id)

    col = 4

    for i, r in enumerate(rows, start=1):

        task = r[1]
        task_name = task.name if task else f"Task {i}"

        fill = task_fill_1 if i % 2 == 1 else task_fill_2

        ws.merge_cells(start_row=start_row, start_column=col,
                       end_row=start_row, end_column=col+1)

        cell = ws.cell(row=start_row, column=col, value=task_name)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_align
        cell.border = border

        ws.cell(row=start_row+1, column=col, value="Actual Start")
        ws.cell(row=start_row+1, column=col+1, value="Actual Finish")

        ws.cell(row=start_row+1, column=col).fill = fill
        ws.cell(row=start_row+1, column=col+1).fill = fill

        col += 2

    data_row = start_row + 2

    # ✅ DATA
    for scope in scopes:

        ws.cell(row=data_row, column=1, value=scope.circle)
        ws.cell(row=data_row, column=2, value=scope.node_id)
        ws.cell(row=data_row, column=3, value=scope.facility_name)

        rows = get_task_execution_for_scope(db, scope.id)

        col = 4

        for idx, r in enumerate(rows, start=1):
            exec_row = r[0]

            fill = task_fill_1 if idx % 2 == 1 else task_fill_2

            ws.cell(row=data_row, column=col, value=exec_row.actual_start)
            ws.cell(row=data_row, column=col+1, value=exec_row.actual_finish)

            ws.cell(row=data_row, column=col).fill = fill
            ws.cell(row=data_row, column=col+1).fill = fill

            col += 2

        data_row += 1

    # ✅ BORDER + ALIGN
    for row in ws.iter_rows(min_row=start_row, max_row=data_row, min_col=1, max_col=ws.max_column):
        for cell in row:
            cell.border = border
            cell.alignment = center_align

    # ✅ FREEZE
    ws.freeze_panes = ws[f"D{start_row+2}"]

    # ✅ WIDTH
    for col_idx in range(1, ws.max_column + 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = 18

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition":
            f'attachment; filename="{file_name}"'
        }
    )    
    
        
@router.post("/circle/{circle}/upload")
def upload_circle_execution(
    circle: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    try:
        

        # ✅ FIX 1 — Read file ONCE (important)
        df = pd.read_excel(file.file, header=None)

        # ✅ find header row
        header_row_index = None
        for i, row in df.iterrows():
            values = [str(x).strip().lower() for x in row if pd.notna(x)]
            if "node" in values:
                header_row_index = i
                break

        if header_row_index is None:
            raise HTTPException(status_code=400, detail="❌ Node header not found")

        # ✅ reload correctly
        file.file.seek(0)  # 🔥 IMPORTANT FIX
        df = pd.read_excel(file.file, header=header_row_index)

        # ✅ clean columns
        df.columns = [str(col).strip() for col in df.columns]

        scopes = db.query(Scope).filter(Scope.circle == circle).all()
        scope_map = {s.node_id.strip(): s for s in scopes}

        for _, row in df.iterrows():

            node = str(row["Node"]).strip()

            if node not in scope_map:
                print("Skipping unknown node:", node)
                continue

            scope = scope_map[node]

            rows = get_task_execution_for_scope(db, scope.id)

            columns = df.columns.tolist()
            
            # ✅ Start after Facility column
            col_index = columns.index("Facility") + 1
            
            for idx, r in enumerate(rows):
            
                exec_row = r[0]
            
                start_col = columns[col_index]
                finish_col = columns[col_index + 1]
            
                actual_start = row[start_col]
                actual_finish = row[finish_col]
            
                # ✅ convert safely
                actual_start = pd.to_datetime(actual_start, errors="coerce")
                actual_finish = pd.to_datetime(actual_finish, errors="coerce")
            
                actual_start = actual_start.date() if pd.notna(actual_start) else None
                actual_finish = actual_finish.date() if pd.notna(actual_finish) else None
            
                # ✅ update DB
                exec_row.actual_start = actual_start
                exec_row.actual_finish = actual_finish
            
                # ✅ status
                if actual_finish:
                    exec_row.status = "Completed"
                elif actual_start:
                    exec_row.status = "In Progress"
                else:
                    exec_row.status = "Not Started"
            
                # ✅ delay
                if actual_finish and exec_row.planned_finish:
                    delay = (actual_finish - exec_row.planned_finish).days
                    exec_row.delay_days = max(0, delay)
                else:
                    exec_row.delay_days = 0
            
                col_index += 2


        db.commit()

        return {"message": f"✅ Circle '{circle}' uploaded successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/project/{project_id}/upload")
def upload_project_execution(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    

    df = pd.read_excel(file.file, header=None)

    header_row_index = None

    # ✅ detect header row
    for i, row in df.iterrows():
        values = [str(x).strip().lower() for x in row if pd.notna(x)]
        if "node" in values:
            header_row_index = i
            break

    if header_row_index is None:
        raise HTTPException(status_code=400, detail="❌ Node header not found")

    file.file.seek(0)
    df = pd.read_excel(file.file, header=header_row_index)
    df.columns = [str(col).strip() for col in df.columns]

    scopes = db.query(Scope).filter(Scope.project_id == project_id).all()
    scope_map = {s.node_id.strip(): s for s in scopes}

    for _, row in df.iterrows():

        node = str(row["Node"]).strip()

        if node not in scope_map:
            continue

        scope = scope_map[node]

        rows = get_task_execution_for_scope(db, scope.id)
        columns = df.columns.tolist()

        col_index = columns.index("Facility") + 1

        for idx, r in enumerate(rows):

            exec_row = r[0]

            start_col = columns[col_index]
            finish_col = columns[col_index + 1]

            actual_start = row[start_col]
            actual_finish = row[finish_col]

            actual_start = pd.to_datetime(actual_start, errors="coerce")
            actual_finish = pd.to_datetime(actual_finish, errors="coerce")

            actual_start = actual_start.date() if pd.notna(actual_start) else None
            actual_finish = actual_finish.date() if pd.notna(actual_finish) else None

            exec_row.actual_start = actual_start
            exec_row.actual_finish = actual_finish

            if actual_finish:
                exec_row.status = "Completed"
            elif actual_start:
                exec_row.status = "In Progress"
            else:
                exec_row.status = "Not Started"

            if actual_finish and exec_row.planned_finish:
                delay = (actual_finish - exec_row.planned_finish).days
                exec_row.delay_days = max(0, delay)
            else:
                exec_row.delay_days = 0

            col_index += 2

    db.commit()

    return {"message": "✅ Project uploaded successfully"}

@router.post("/projects/{project_id}/revise-plan")
def revise_plan(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    user = require_login(request)

    # ✅ Only admin allowed
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # ✅ Must be locked (execution started)
    if not project.baseline_locked:
        raise HTTPException(
            status_code=400,
            detail="Cannot revise before execution starts"
        )

    # ✅ Fetch all execution rows
    executions = db.query(TaskExecution).filter(
        TaskExecution.project_id == project_id
    ).all()

    for exec_row in executions:

        # ✅ Create revised plan safely
        exec_row.revised_start = exec_row.actual_start or exec_row.planned_start
        exec_row.revised_finish = exec_row.planned_finish

        # ✅ Increment version
        exec_row.plan_version = (exec_row.plan_version or 1) + 1

    db.commit()

    
    return RedirectResponse(
        f"/projects/{project.programme_id}?success=revise",
        status_code=303
    )


from fastapi import UploadFile, File, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import pandas as pd

@router.post("/projects/{project_id}/upload-revised-plan")
def upload_revised_plan(
    project_id: int,
    file: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db)
):
    user = require_login(request)

    # ✅ Admin check
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.baseline_locked:
        raise HTTPException(
            status_code=400,
            detail="Cannot revise before execution starts"
        )

    import pandas as pd

    # ✅ READ EXCEL
    try:
        df = pd.read_excel(file.file)
        df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid Excel file")

    # ✅ REQUIRED COLUMN (only task_id mandatory now)
    if "task_id" not in df.columns:
        raise HTTPException(
            status_code=400,
            detail="Missing required column: task_id"
        )

    # ✅ DATE CONVERTER
    def convert_excel_date(value):
        try:
            if value is None or pd.isna(value):
                return None

            if isinstance(value, pd.Timestamp):
                return value.date()

            if isinstance(value, (int, float)):
                return pd.to_datetime(value, unit='d', origin='1899-12-30').date()

            return pd.to_datetime(value).date()

        except Exception:
            return None

    updates_count = 0

    # ✅ PROCESS ROWS
    for _, row in df.iterrows():

        # ✅ Get task_id safely
        try:
            task_id = int(row["task_id"])
        except:
            continue

        # ✅ DETERMINE LEVEL
        if "scope_id" in df.columns and not pd.isna(row.get("scope_id")):
            exec_rows = db.query(TaskExecution).filter(
                TaskExecution.scope_id == int(row["scope_id"]),
                TaskExecution.task_id == task_id
            ).all()

        elif "circle" in df.columns and row.get("circle"):
            exec_rows = db.query(TaskExecution).join(Scope).filter(
                Scope.circle == row["circle"],
                TaskExecution.task_id == task_id
            ).all()

        else:
            exec_rows = db.query(TaskExecution).join(Scope).filter(
                Scope.project_id == project_id,
                TaskExecution.task_id == task_id
            ).all()

        if not exec_rows:
            continue

        # ✅ GET REVISED VALUES (priority logic)
        revised_start = convert_excel_date(
            row.get("revised_start")
        ) or convert_excel_date(row.get("planned_start"))

        revised_finish = convert_excel_date(
            row.get("revised_finish")
        ) or convert_excel_date(row.get("planned_finish"))

        # ✅ Skip invalid rows
        if revised_start is None or revised_finish is None:
            continue

        # ✅ UPDATE
        for exec_row in exec_rows:

            # ✅ Skip if no change
            if (
                exec_row.revised_start == revised_start and
                exec_row.revised_finish == revised_finish
            ):
                continue

            exec_row.revised_start = revised_start
            exec_row.revised_finish = revised_finish
            exec_row.plan_version = (exec_row.plan_version or 1) + 1

            updates_count += 1

    db.commit()

    return RedirectResponse(
        f"/projects/{project.programme_id}?success=upload",
        status_code=303
    )

@router.get("/projects/{project_id}/download-revision-template")
def download_revision_template(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    user = require_login(request)

    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    import pandas as pd
    from openpyxl.styles import Font, PatternFill

    # ✅ Fetch data
    rows = db.query(TaskExecution, Scope, Task).join(
        Scope, TaskExecution.scope_id == Scope.id
    ).join(
        Task, TaskExecution.task_id == Task.id
    ).filter(
        Scope.project_id == project_id
    ).all()

    data = []

    for execution, scope, task in rows:
        data.append({
            "scope_id": execution.scope_id,
            "scope_name": scope.node_id if scope else "",
            "circle": scope.circle if scope else "",
            "task_id": execution.task_id,
            "task_name": task.name if task else "",
            "planned_start": execution.planned_start,
            "planned_finish": execution.planned_finish,
            "revised_start": execution.revised_start,
            "revised_finish": execution.revised_finish
        })

    df = pd.DataFrame(data)

    output = BytesIO()
    
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
    

        # ✅ ✅ SHEET 1 → DATA
        df.to_excel(writer, sheet_name="Revision_Data", index=False)

        data_ws = writer.sheets["Revision_Data"]

        red_fill = PatternFill(start_color="F8CBAD", fill_type="solid")
        green_fill = PatternFill(start_color="E2F0D9", fill_type="solid")

        # ✅ Highlight headers (IMPORTANT UX)
        for col_idx, col_name in enumerate(df.columns, start=1):
            cell = data_ws.cell(row=1, column=col_idx)

            if col_name in ["scope_id", "task_id", "task_name"]:
                cell.fill = red_fill
                cell.font = Font(bold=True)

            if col_name in ["revised_start", "revised_finish"]:
                cell.fill = green_fill
                cell.font = Font(bold=True)

        # ✅ ✅ SHEET 2 → CLEAN INSTRUCTION TABLE
        instructions_df = pd.DataFrame({
            "Section": [
                "⚠ DO NOT CHANGE",
                "✅ EDIT ONLY",
                "🟢 NODE LEVEL",
                "🔵 CIRCLE LEVEL",
                "🟡 PROJECT LEVEL",
                "📌 RULES",
                "✅ PROCESS"
            ],
            "Details": [
                "scope_id, task_id, task_name",
                "revised_start, revised_finish",
                "Update rows for specific scope_id",
                "Filter rows using 'circle'",
                "Update all rows for full project",
                "Do not delete rows / keep format intact",
                "Download → Edit → Upload"
            ]
        })

        instructions_df.to_excel(writer, sheet_name="Instructions", index=False)

        ws = writer.sheets["Instructions"]

        blue_fill = PatternFill(start_color="DCE6F1", fill_type="solid")
        green_fill2 = PatternFill(start_color="E2F0D9", fill_type="solid")
        red_fill2 = PatternFill(start_color="F8CBAD", fill_type="solid")
        yellow_fill = PatternFill(start_color="FFF2CC", fill_type="solid")

        bold = Font(bold=True)

        # ✅ Highlight rows (safe — no corruption)
        for row_idx in range(2, ws.max_row + 1):
            section = ws.cell(row=row_idx, column=1).value

            if "DO NOT" in section:
                ws.cell(row=row_idx, column=1).fill = red_fill2
                ws.cell(row=row_idx, column=1).font = bold

            elif "EDIT ONLY" in section:
                ws.cell(row=row_idx, column=1).fill = green_fill2
                ws.cell(row=row_idx, column=1).font = bold

            elif "NODE LEVEL" in section or "CIRCLE LEVEL" in section:
                ws.cell(row=row_idx, column=1).fill = blue_fill

            elif "PROJECT LEVEL" in section:
                ws.cell(row=row_idx, column=1).fill = yellow_fill

            elif "RULES" in section:
                ws.cell(row=row_idx, column=1).fill = red_fill2

            elif "PROCESS" in section:
                ws.cell(row=row_idx, column=1).fill = green_fill2

        # ✅ Autofit columns (nice UX)
        ws.column_dimensions["A"].width = 22
        ws.column_dimensions["B"].width = 55
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition":
            f'attachment; filename="Revision_Template_Project_{project_id}.xlsx"'
        }
    )