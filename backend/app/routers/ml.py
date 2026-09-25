from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.schemas.job import (
    SalaryPredictRequest, SalaryPredictResponse,
    RoleClassifyRequest, RoleClassifyResponse,
)
from backend.app.services import ml_service
from backend.app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/ml", tags=["ml"])


@router.post("/predict-salary", response_model=SalaryPredictResponse)
def predict_salary(payload: SalaryPredictRequest, current_user: User = Depends(get_current_user)):
    try:
        result = ml_service.predict_salary(
            job_title=payload.job_title, location=payload.location,
            experience=payload.experience, industry=payload.industry,
            work_mode=payload.work_mode, skills=payload.skills,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return result


@router.post("/classify-role", response_model=RoleClassifyResponse)
def classify_role(payload: RoleClassifyRequest, current_user: User = Depends(get_current_user)):
    try:
        result = ml_service.classify_role(payload.job_description)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return result
