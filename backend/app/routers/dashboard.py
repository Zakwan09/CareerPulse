from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.services import analytics_service
from backend.app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {
        **analytics_service.dashboard_summary(db),
        "jobs_by_role": analytics_service.jobs_by_field(db, "job_title")[:10],
        "jobs_by_location": analytics_service.jobs_by_field(db, "location")[:10],
        "salary_distribution": analytics_service.salary_distribution(db),
        "experience_distribution": analytics_service.experience_distribution(db),
        "top_skills": analytics_service.top_skills(db, limit=10),
    }
