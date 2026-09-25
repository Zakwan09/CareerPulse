from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.job import Job
from backend.app.models.user import User
from backend.app.services import analytics_service
from backend.app.services.auth_service import get_current_user

router = APIRouter(prefix="/api", tags=["analytics"])


@router.get("/market/overview")
def market_overview(
    role: Optional[str] = None,
    location: Optional[str] = None,
    industry: Optional[str] = None,
    work_mode: Optional[str] = None,
    employment_type: Optional[str] = None,
    min_experience: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = {
        "role": role, "location": location, "industry": industry,
        "work_mode": work_mode, "employment_type": employment_type,
        "min_experience": min_experience,
    }
    return analytics_service.market_overview(db, filters)


@router.get("/roles")
def roles(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = db.query(Job.job_title).distinct().all()
    return {"roles": sorted(r[0] for r in rows)}


@router.get("/locations")
def locations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = db.query(Job.location).distinct().all()
    return {"locations": sorted(r[0] for r in rows)}
