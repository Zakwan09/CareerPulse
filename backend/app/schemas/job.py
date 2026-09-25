from datetime import date
from typing import Optional, List
from pydantic import BaseModel


class JobOut(BaseModel):
    id: int
    external_job_id: str
    job_title: str
    company: Optional[str]
    location: Optional[str]
    country: Optional[str]
    experience_min: Optional[float]
    experience_max: Optional[float]
    salary_min: Optional[float]
    salary_max: Optional[float]
    currency: Optional[str]
    employment_type: Optional[str]
    work_mode: Optional[str]
    industry: Optional[str]
    posted_date: Optional[date]
    skills: List[str] = []

    class Config:
        from_attributes = True


class SalaryPredictRequest(BaseModel):
    job_title: str
    location: str
    experience: float
    industry: Optional[str] = None
    work_mode: Optional[str] = None
    skills: List[str] = []


class SalaryPredictResponse(BaseModel):
    predicted_salary_lpa: float
    model_used: str


class RoleClassifyRequest(BaseModel):
    job_description: str


class RoleClassifyResponse(BaseModel):
    predicted_role: str
    confidence: Optional[float] = None
    method: str
