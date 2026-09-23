# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra
"""

# -*- coding: utf-8 -*-
"""
Scope routes – Enterprise‑grade implementation
"""

from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import RedirectResponse, HTMLResponse
import pandas as pd

from database import get_db
from models import Scope
from contextlib import contextmanager

router = APIRouter()

# ---------------- DB CONTEXT ----------------
@contextmanager
def get_db_ctx():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


# ====================================================
# BULK SCOPE UPLOAD (REPLACE MODE – ENTERPRISE SAFE)
# ====================================================
@router.post("/project/{project_id}/scope/upload")
def upload_scope_excel(project_id: int, file: UploadFile = File(...)):

    # ------------------------------
    # Validate file type
    # ------------------------------
    if not file.filename.lower().endswith(".xlsx"):
        return RedirectResponse(
            f"/project/{project_id}/scopes",
            status_code=303
        )

    # ------------------------------
    # Read Excel
    # ------------------------------
    df = pd.read_excel(file.file)

    # ------------------------------
    # Required columns
    # ------------------------------
    required_columns = [
        "Priority",
        "Circle",
        "Facility_Name",
        "Node_ID",
        "No_Of_Servers",
    ]

    for col in required_columns:
        if col not in df.columns:
            return HTMLResponse(
                f"<h3>Scope upload failed: Missing column '{col}'</h3>",
                status_code=400
            )

    # ====================================================
    # ✅ LAYER‑1: NORMALIZE INPUT (DEFENSIVE)
    # ====================================================
    df["Node_ID"] = (
        df["Node_ID"]
        .astype(str)
        .str.strip()
        .str.replace(" ", "", regex=False)
    )

    df["Circle"] = df["Circle"].astype(str).str.strip()
    df["Facility_Name"] = df["Facility_Name"].astype(str).str.strip()

    # Remove empty Node IDs (in case headers got repeated)
    df = df[df["Node_ID"].notna() & (df["Node_ID"] != "")]

    # ====================================================
    # ✅ LAYER‑2: DEDUPLICATE WITHIN FILE
    # ====================================================
    original_count = len(df)
    df = df.drop_duplicates(subset=["Node_ID"], keep="first")
    duplicate_count = original_count - len(df)

    # ====================================================
    # Prepare ORM objects
    # ====================================================
    scopes_to_insert = []

    for _, row in df.iterrows():
        scopes_to_insert.append(
            Scope(
                project_id=project_id,
                priority=int(row["Priority"]),
                circle=row["Circle"],
                facility_name=row["Facility_Name"],
                node_id=row["Node_ID"],
                num_servers=int(row["No_Of_Servers"]),
                status="Not Started",
            )
        )

    # ====================================================
    # ✅ LAYER‑3: REPLACE EXISTING SCOPE
    # ✅ LAYER‑4: SAFE BULK INSERT
    # ====================================================
    with get_db_ctx() as db:
        try:
            # Replace mode: clear existing scope for project
            db.query(Scope).filter(Scope.project_id == project_id).delete()
            db.flush()

            if scopes_to_insert:
                db.bulk_save_objects(scopes_to_insert)

            db.commit()

        except Exception:
            db.rollback()
            raise

    # ====================================================
    # Redirect back to scope page
    # ====================================================
    return RedirectResponse(
        f"/project/{project_id}/scopes",
        status_code=303
    )


# ====================================================
# MANUAL SCOPE ADD (SINGLE NODE)
# ====================================================
@router.post("/project/{project_id}/scope/add")
def add_scope_manual(
    project_id: int,
    priority: int = Form(...),
    circle: str = Form(...),
    facility_name: str = Form(...),
    node_id: str = Form(...),
    num_servers: int = Form(...)
):
    with get_db_ctx() as db:
        scope = Scope(
            project_id=project_id,
            priority=priority,
            circle=circle.strip(),
            facility_name=facility_name.strip(),
            node_id=node_id.strip().replace(" ", ""),
            num_servers=num_servers,
            status="Not Started",
        )
        db.add(scope)
        db.commit()

    return RedirectResponse(
        f"/project/{project_id}/scopes",
        status_code=303
    )