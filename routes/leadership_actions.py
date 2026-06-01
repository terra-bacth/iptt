from fastapi import (
    APIRouter,
    Request,
    Depends,
    Form
)

from fastapi.responses import (
    RedirectResponse
)

from datetime import datetime
from sqlalchemy.orm import Session

from database import get_db

from services.reporting.leadership_actions import (

    create_leadership_action,

    update_leadership_action,

    delete_leadership_action
)

router = APIRouter()


# =========================================
# CREATE ACTION
# =========================================

@router.post(
    "/leadership-actions/create"
)
def create_action(

    project_id: int = Form(...),

    action: str = Form(...),

    owner: str = Form(...),

    priority: str = Form(...),

    target_date: str = Form(...),
    
    status: str = Form(...),

    remarks: str = Form(""),

    db: Session = Depends(get_db)
):

    create_leadership_action(

        project_id=project_id,

        action=action,

        owner=owner,

        priority=priority,
        
        status=status,

        target_date=datetime.strptime(
            target_date,
            "%Y-%m-%d"
        ).date(),

        remarks=remarks,

        db=db
    )

    return RedirectResponse(

        url=f"/project/{project_id}/executive-dashboard",

        status_code=303
    )


# =========================================
# UPDATE ACTION
# =========================================

@router.post(
    "/leadership-actions/update/{action_id}"
)
def update_action(

    action_id: int,

    project_id: int = Form(...),

    status: str = Form(...),
    
    priority: str = Form(...),

    target_date: str = Form(...),

    remarks: str = Form(""),

    db: Session = Depends(get_db)
):

    update_leadership_action(

        action_id=action_id,
    
        status=status,
    
        priority=priority,
    
        target_date=datetime.strptime(
            target_date,
            "%Y-%m-%d"
        ).date(),
    
        remarks=remarks,
    
        db=db
    )

    return RedirectResponse(

        url=f"/project/{project_id}/executive-dashboard",

        status_code=303
    )


# =========================================
# DELETE ACTION
# =========================================

@router.post(
    "/leadership-actions/delete/{action_id}"
)
def delete_action(

    action_id: int,

    project_id: int = Form(...),

    db: Session = Depends(get_db)
):

    delete_leadership_action(

        action_id=action_id,

        db=db
    )

    return RedirectResponse(

        url=f"/project/{project_id}/executive-dashboard",

        status_code=303
    )