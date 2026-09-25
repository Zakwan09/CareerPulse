"""
Candidate Skill-Gap Engine.

Determines the skills actually required for a target role from the live job
dataset (not a hard-coded list), compares them against the candidate's
current skills, and scores + prioritizes the missing ones.

Resume support:
- PDF
- DOCX

Resume skills are extracted using the skills already stored in the
CareerPulse database. The extracted skills are then passed into the
existing skill-gap engine below.

--- Weighted match score formula -------------------------------------------
For each market-required skill i associated with the target role:
    weight_i = demand_pct_i (0-100, how many target-role jobs need it)
    matched contribution   = weight_i if candidate has it, else 0

weighted_match_score = sum(matched contributions) / sum(all weights) * 100

--- Learning priority score formula ----------------------------------------
For each missing skill:
    priority_score = 0.45 * demand_pct_in_role
                    + 0.25 * overall_market_demand_pct
                    + 0.20 * growth_score
                    + 0.10 * salary_association_score

Buckets:
    score >= 60 -> High
    30-59       -> Medium
    else        -> Low

All inputs are computed from the database.
"""

from collections import Counter
from typing import List
import io
import re

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.models.job import Job
from backend.app.models.skill import Skill, JobSkill
from backend.app.services.analytics_service import skill_trend
from backend.app.utils.skill_normalizer import normalize_skill


# ============================================================
# RESUME TEXT EXTRACTION
# ============================================================

def _extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF resume."""

    try:
        from pypdf import PdfReader
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="PDF support is not installed. Run: pip install pypdf"
        )

    try:
        reader = PdfReader(io.BytesIO(file_bytes))

        pages = []

        for page in reader.pages:
            text = page.extract_text()

            if text:
                pages.append(text)

        return "\n".join(pages)

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not read PDF resume: {exc}"
        )


def _extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from a DOCX resume."""

    try:
        from docx import Document
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="DOCX support is not installed. Run: pip install python-docx"
        )

    try:
        document = Document(
            io.BytesIO(file_bytes)
        )

        parts = []

        # Normal paragraphs
        for paragraph in document.paragraphs:
            text = paragraph.text.strip()

            if text:
                parts.append(text)

        # Also read tables because many resumes store
        # skills/experience inside tables.
        for table in document.tables:

            for row in table.rows:

                for cell in row.cells:

                    text = cell.text.strip()

                    if text:
                        parts.append(text)

        return "\n".join(parts)

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not read DOCX resume: {exc}"
        )


def _extract_resume_text(
    file_bytes: bytes,
    filename: str
) -> str:
    """Extract readable text from PDF or DOCX."""

    filename = filename.lower().strip()

    if filename.endswith(".pdf"):
        return _extract_text_from_pdf(file_bytes)

    if filename.endswith(".docx"):
        return _extract_text_from_docx(file_bytes)

    raise HTTPException(
        status_code=400,
        detail="Only PDF and DOCX resumes are supported."
    )


# ============================================================
# RESUME SKILL EXTRACTION
# ============================================================

def extract_resume_skills(
    db: Session,
    file_bytes: bytes,
    filename: str
) -> List[str]:
    """
    Extract skills from a resume.

    Skills are matched against the CareerPulse Skill table.
    This means the resume analyzer uses the same skill vocabulary
    as the job-market dataset.
    """

    text = _extract_resume_text(
        file_bytes,
        filename
    )

    if not text.strip():
        raise HTTPException(
            status_code=400,
            detail=(
                "No readable text was found in the resume. "
                "If this is a scanned/image-only PDF, OCR is required."
            )
        )

    text_lower = text.lower()

    # Get all skills already known by CareerPulse.
    skills = db.query(Skill).all()

    detected = []
    detected_normalized = set()

    # Check longer skill names first.
    # Example:
    # "Machine Learning" should be checked before "Machine".
    skills = sorted(
        skills,
        key=lambda skill: len(
            getattr(skill, "normalized_name", "")
            or getattr(skill, "skill_name", "")
            or ""
        ),
        reverse=True
    )

    for skill_obj in skills:

        skill_name = (
            getattr(
                skill_obj,
                "normalized_name",
                None
            )
            or
            getattr(
                skill_obj,
                "skill_name",
                None
            )
        )

        if not skill_name:
            continue

        skill_name = skill_name.strip()

        if not skill_name:
            continue

        normalized = normalize_skill(skill_name)

        if not normalized:
            continue

        normalized_lower = normalized.lower()

        if normalized_lower in detected_normalized:
            continue

        # Word-boundary matching.
        #
        # This prevents:
        # SQL from matching inside "NoSQL"
        # R from matching random letters
        # etc.
        pattern = (
            r"(?<!\w)"
            + re.escape(skill_name.lower())
            + r"(?!\w)"
        )

        if re.search(pattern, text_lower):

            detected.append(normalized)
            detected_normalized.add(normalized_lower)

    return detected


# ============================================================
# EXISTING SKILL-GAP ENGINE
# ============================================================

def _role_required_skills(
    db: Session,
    target_role: str
) -> list[dict]:
    """Skills associated with jobs matching target_role."""

    jobs = (
        db.query(Job)
        .filter(
            Job.job_title.ilike(
                f"%{target_role}%"
            )
        )
        .all()
    )

    if not jobs:
        return []

    job_ids = [
        job.id
        for job in jobs
    ]

    skill_rows = (
        db.query(JobSkill, Skill)
        .join(Skill)
        .filter(
            JobSkill.job_id.in_(job_ids)
        )
        .all()
    )

    counts = Counter(
        skill.normalized_name
        for _, skill in skill_rows
    )

    number_of_jobs = len(jobs)

    return [
        {
            "skill": skill,
            "count": count,
            "demand_pct_in_role": round(
                100 * count / number_of_jobs,
                1
            )
        }
        for skill, count
        in counts.most_common()
    ]


def _overall_market_demand(
    db: Session,
    skill_name: str
) -> float:

    total_jobs = (
        db.query(Job).count()
        or 1
    )

    skill = (
        db.query(Skill)
        .filter(
            Skill.normalized_name == skill_name
        )
        .first()
    )

    if not skill:
        return 0.0

    count = (
        db.query(JobSkill)
        .filter(
            JobSkill.skill_id == skill.id
        )
        .count()
    )

    return round(
        100 * count / total_jobs,
        1
    )


def _growth_score(
    db: Session,
    skill_name: str
) -> float:

    trend = skill_trend(
        db,
        skill_name
    )

    if len(trend) < 2:
        return 50.0

    previous = trend[-2]["count"]
    current = trend[-1]["count"]

    if previous == 0:
        return (
            100.0
            if current > 0
            else 0.0
        )

    growth = (
        (current - previous)
        / previous
    )

    return max(
        0.0,
        min(
            100.0,
            50 + growth * 100
        )
    )


def _salary_association_score(
    db: Session,
    skill_name: str
) -> float:

    skill = (
        db.query(Skill)
        .filter(
            Skill.normalized_name == skill_name
        )
        .first()
    )

    if not skill:
        return 0.0

    job_ids = [
        job_skill.job_id
        for job_skill
        in db.query(JobSkill)
        .filter(
            JobSkill.skill_id == skill.id
        )
        .all()
    ]

    if not job_ids:
        return 0.0

    jobs = (
        db.query(Job)
        .filter(
            Job.id.in_(job_ids)
        )
        .all()
    )

    with_skill_avg = (
        sum(
            (
                (job.salary_min or 0)
                +
                (job.salary_max or 0)
            ) / 2
            for job in jobs
        )
        / len(jobs)
    )

    all_jobs = db.query(Job).all()

    overall_avg = (
        sum(
            (
                (job.salary_min or 0)
                +
                (job.salary_max or 0)
            ) / 2
            for job in all_jobs
        )
        / len(all_jobs)
        if all_jobs
        else with_skill_avg
    )

    if overall_avg == 0:
        return 50.0

    ratio = (
        with_skill_avg
        / overall_avg
    )

    return max(
        0.0,
        min(
            100.0,
            ratio * 50
        )
    )


# ============================================================
# MAIN ANALYSIS
# ============================================================

def analyze_skill_gap(
    db: Session,
    target_role: str,
    current_skills: List[str]
) -> dict:

    required = _role_required_skills(
        db,
        target_role
    )

    candidate_norm = {
        normalize_skill(skill)
        for skill in current_skills
    }

    if not required:

        return {
            "target_role": target_role,
            "matched_skills": [],
            "missing_skills": [],
            "match_percentage": 0.0,
            "weighted_match_score": 0.0,
            "learning_priorities": [],
            "note": (
                f"No jobs found in the dataset "
                f"matching role '{target_role}'."
            )
        }

    matched = [
        requirement["skill"]
        for requirement in required
        if requirement["skill"]
        in candidate_norm
    ]

    missing = [
        requirement
        for requirement in required
        if requirement["skill"]
        not in candidate_norm
    ]

    match_percentage = round(
        100 * len(matched)
        / len(required),
        1
    )

    total_weight = (
        sum(
            requirement["demand_pct_in_role"]
            for requirement in required
        )
        or 1
    )

    matched_weight = sum(
        requirement["demand_pct_in_role"]
        for requirement in required
        if requirement["skill"]
        in candidate_norm
    )

    weighted_score = round(
        100
        * matched_weight
        / total_weight,
        1
    )

    priorities = []

    for requirement in missing:

        skill = requirement["skill"]

        demand_in_role = (
            requirement[
                "demand_pct_in_role"
            ]
        )

        overall_demand = (
            _overall_market_demand(
                db,
                skill
            )
        )

        growth = _growth_score(
            db,
            skill
        )

        salary_assoc = (
            _salary_association_score(
                db,
                skill
            )
        )

        score = (
            0.45 * demand_in_role
            + 0.25 * overall_demand
            + 0.20 * growth
            + 0.10 * salary_assoc
        )

        if score >= 60:
            level = "High"

        elif score >= 30:
            level = "Medium"

        else:
            level = "Low"

        reasons = [
            (
                f"Required in "
                f"{demand_in_role}% of "
                f"{target_role} postings"
            )
        ]

        if overall_demand >= 30:

            reasons.append(
                "Strong overall market presence "
                f"({overall_demand}% of all jobs)"
            )

        if growth > 60:

            reasons.append(
                "Demand trending upward recently"
            )

        if salary_assoc > 55:

            reasons.append(
                "Associated with above-average salaries"
            )

        priorities.append(
            {
                "skill": skill,
                "priority": level,
                "priority_score": round(
                    score,
                    1
                ),
                "reasons": reasons,
            }
        )

    priorities.sort(
        key=lambda priority:
            priority["priority_score"],
        reverse=True
    )

    return {
        "target_role": target_role,
        "matched_skills": matched,
        "missing_skills": [
            requirement["skill"]
            for requirement in missing
        ],
        "match_percentage": match_percentage,
        "weighted_match_score": weighted_score,
        "learning_priorities": priorities,
    }