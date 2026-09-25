from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, Index
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    external_job_id = Column(String(64), unique=True, index=True, nullable=False)
    job_title = Column(String(150), index=True, nullable=False)
    company = Column(String(150), index=True)
    location = Column(String(100), index=True)
    country = Column(String(100))
    experience_min = Column(Float)
    experience_max = Column(Float)
    salary_min = Column(Float)
    salary_max = Column(Float)
    currency = Column(String(20))
    employment_type = Column(String(50))
    work_mode = Column(String(30))
    industry = Column(String(100), index=True)
    job_description = Column(Text)
    posted_date = Column(Date, index=True)
    source = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    job_skills = relationship("JobSkill", back_populates="job", cascade="all, delete-orphan")


Index("ix_jobs_title_location", Job.job_title, Job.location)
