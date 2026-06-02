# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra
"""

from fastapi import Request
from auth.dependencies import require_admin
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from schemas import ProgrammeCreate, ProgrammeResponse
from services import programme_service

router = APIRouter()

@router.post("/", response_model=ProgrammeResponse)
def add_programme(
    data: ProgrammeCreate,
    request: Request,
    db: Session = Depends(get_db)
):
       
    require_admin(request)  # ✅ this will now HARD STOP

    return programme_service.create_programme(
        db, data.name, data.status
    )


@router.get("/", response_model=list[ProgrammeResponse])
def list_programmes(db: Session = Depends(get_db)):
    return programme_service.get_programmes(db)