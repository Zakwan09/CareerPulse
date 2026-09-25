from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    skill_name = Column(String(120), nullable=False)          # as first seen
    normalized_name = Column(String(120), unique=True, index=True, nullable=False)
    category = Column(String(50), index=True)

    job_skills = relationship("JobSkill", back_populates="skill", cascade="all, delete-orphan")


class JobSkill(Base):
    __tablename__ = "job_skills"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), index=True, nullable=False)
    skill_id = Column(Integer, ForeignKey("skills.id"), index=True, nullable=False)

    job = relationship("Job", back_populates="job_skills")
    skill = relationship("Skill", back_populates="job_skills")
