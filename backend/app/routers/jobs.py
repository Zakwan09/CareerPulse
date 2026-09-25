from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.job import Job
from backend.app.models.skill import Skill, JobSkill
from backend.app.models.user import User
from backend.app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _job_to_dict(db: Session, job: Job) -> dict:
    skills = [
        s.normalized_name for s in
        db.query(Skill).join(JobSkill).filter(JobSkill.job_id == job.id).all()
    ]
    return {
        "id": job.id,
        "external_job_id": job.external_job_id,
        "job_title": job.job_title,
        "company": job.company,
        "location": job.location,
        "country": job.country,
        "experience_min": job.experience_min,
        "experience_max": job.experience_max,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "currency": job.currency,
        "employment_type": job.employment_type,
        "work_mode": job.work_mode,
        "industry": job.industry,
        "posted_date": str(job.posted_date) if job.posted_date else None,
        "skills": skills,
    }


@router.get("")
def list_jobs(
    limit: int = 50, offset: int = 0,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    jobs = db.query(Job).order_by(Job.posted_date.desc()).offset(offset).limit(limit).all()
    total = db.query(Job).count()
    return {"total": total, "results": [_job_to_dict(db, j) for j in jobs]}


@router.get("/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return _job_to_dict(db, job)

