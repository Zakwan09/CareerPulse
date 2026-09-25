from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.services import forecast_service
from backend.app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/forecast", tags=["forecast"])


@router.get("/{skill_name}")
def forecast_skill(skill_name: str, periods_ahead: int = 2,
                    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return forecast_service.forecast_skill(db, skill_name, periods_ahead)
