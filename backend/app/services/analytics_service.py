"""
All EDA/analytics numbers shown in the UI are computed here, live, from the
database. Nothing in this file is hard-coded to a specific dataset size.
"""
from collections import Counter, defaultdict
from statistics import median
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.models.job import Job
from backend.app.models.skill import Skill, JobSkill


def dashboard_summary(db: Session) -> dict:
    total_jobs = db.query(Job).count()
    total_skills = db.query(Skill).count()

    top_role_row = (
        db.query(Job.job_title, func.count(Job.id).label("cnt"))
        .group_by(Job.job_title)
        .order_by(func.count(Job.id).desc())
        .first()
    )
    top_role = top_role_row[0] if top_role_row else None

    salaries = [row[0] for row in db.query((Job.salary_min + Job.salary_max) / 2.0).all()]
    median_salary = round(median(salaries), 2) if salaries else None

    fastest_growing = fastest_growing_skill(db)

    return {
        "total_jobs": total_jobs,
        "total_skills": total_skills,
        "top_role": top_role,
        "median_salary_lpa": median_salary,
        "fastest_growing_skill": fastest_growing,
    }


def jobs_by_field(db: Session, field: str) -> list[dict]:
    col = getattr(Job, field)
    rows = db.query(col, func.count(Job.id)).group_by(col).order_by(func.count(Job.id).desc()).all()
    return [{"label": r[0], "count": r[1]} for r in rows]


def salary_distribution(db: Session) -> dict:
    salaries = [((j.salary_min or 0) + (j.salary_max or 0)) / 2 for j in db.query(Job).all()]
    if not salaries:
        return {"min": None, "max": None, "avg": None, "median": None, "buckets": []}
    buckets = defaultdict(int)
    for s in salaries:
        bucket = f"{int(s // 5) * 5}-{int(s // 5) * 5 + 5}"
        buckets[bucket] += 1
    return {
        "min": round(min(salaries), 1),
        "max": round(max(salaries), 1),
        "avg": round(sum(salaries) / len(salaries), 1),
        "median": round(median(salaries), 1),
        "buckets": sorted(buckets.items(), key=lambda x: int(x[0].split("-")[0])),
    }


def experience_distribution(db: Session) -> list[dict]:
    counts = Counter()
    for j in db.query(Job).all():
        mid = ((j.experience_min or 0) + (j.experience_max or 0)) / 2
        if mid <= 1:
            band = "0-1 yrs"
        elif mid <= 3:
            band = "1-3 yrs"
        elif mid <= 5:
            band = "3-5 yrs"
        elif mid <= 8:
            band = "5-8 yrs"
        else:
            band = "8+ yrs"
        counts[band] += 1
    order = ["0-1 yrs", "1-3 yrs", "3-5 yrs", "5-8 yrs", "8+ yrs"]
    return [{"label": b, "count": counts.get(b, 0)} for b in order]


def top_skills(db: Session, limit: int = 15) -> list[dict]:
    total_jobs = db.query(Job).count() or 1
    rows = (
        db.query(Skill.normalized_name, Skill.category, func.count(JobSkill.id).label("cnt"))
        .join(JobSkill, JobSkill.skill_id == Skill.id)
        .group_by(Skill.normalized_name, Skill.category)
        .order_by(func.count(JobSkill.id).desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "skill": r[0],
            "category": r[1],
            "frequency": r[2],
            "demand_pct": round(100 * r[2] / total_jobs, 1),
        }
        for r in rows
    ]


def skill_detail(db: Session, skill_name: str) -> Optional[dict]:
    skill = db.query(Skill).filter(func.lower(Skill.normalized_name) == skill_name.lower()).first()
    if not skill:
        return None

    job_ids = [js.job_id for js in db.query(JobSkill).filter(JobSkill.skill_id == skill.id).all()]
    jobs = db.query(Job).filter(Job.id.in_(job_ids)).all() if job_ids else []
    total_jobs = db.query(Job).count() or 1

    roles = Counter(j.job_title for j in jobs)
    locations = Counter(j.location for j in jobs)
    salaries = [((j.salary_min or 0) + (j.salary_max or 0)) / 2 for j in jobs]

    # related skills: co-occurrence within the same jobs
    related = Counter()
    for jid in job_ids:
        other_skill_ids = [
            js.skill_id for js in db.query(JobSkill).filter(JobSkill.job_id == jid).all()
            if js.skill_id != skill.id
        ]
        for sid in other_skill_ids:
            s = db.query(Skill).get(sid)
            if s:
                related[s.normalized_name] += 1

    return {
        "skill": skill.normalized_name,
        "category": skill.category,
        "demand_pct": round(100 * len(jobs) / total_jobs, 1),
        "frequency": len(jobs),
        "top_roles": roles.most_common(5),
        "top_locations": locations.most_common(5),
        "salary_avg_lpa": round(sum(salaries) / len(salaries), 1) if salaries else None,
        "related_skills": [r for r, _ in related.most_common(6)],
        "trend": skill_trend(db, skill.normalized_name),
    }


def skill_trend(db: Session, skill_name: str) -> list[dict]:
    """Monthly posting counts for a skill, used for both display and forecasting input."""
    skill = db.query(Skill).filter(func.lower(Skill.normalized_name) == skill_name.lower()).first()
    if not skill:
        return []
    job_ids = [js.job_id for js in db.query(JobSkill).filter(JobSkill.skill_id == skill.id).all()]
    if not job_ids:
        return []
    jobs = db.query(Job).filter(Job.id.in_(job_ids)).all()
    counts = Counter(j.posted_date.strftime("%Y-%m") for j in jobs if j.posted_date)
    return [{"month": m, "count": c} for m, c in sorted(counts.items())]


def fastest_growing_skill(db: Session) -> Optional[str]:
    """Compares the most recent month of postings vs the prior month, per skill."""
    skills = db.query(Skill).all()
    best_skill, best_growth = None, -1
    for s in skills:
        trend = skill_trend(db, s.normalized_name)
        if len(trend) < 2:
            continue
        prev, curr = trend[-2]["count"], trend[-1]["count"]
        growth = (curr - prev) / prev if prev > 0 else (curr if curr > 0 else 0)
        if growth > best_growth and curr >= 2:
            best_growth, best_skill = growth, s.normalized_name
    return best_skill


def market_overview(db: Session, filters: dict) -> dict:
    q = db.query(Job)
    if filters.get("role"):
        q = q.filter(Job.job_title.ilike(f"%{filters['role']}%"))
    if filters.get("location"):
        q = q.filter(Job.location.ilike(f"%{filters['location']}%"))
    if filters.get("industry"):
        q = q.filter(Job.industry.ilike(f"%{filters['industry']}%"))
    if filters.get("work_mode"):
        q = q.filter(Job.work_mode.ilike(f"%{filters['work_mode']}%"))
    if filters.get("employment_type"):
        q = q.filter(Job.employment_type.ilike(f"%{filters['employment_type']}%"))
    if filters.get("min_experience") is not None:
        q = q.filter(Job.experience_max >= float(filters["min_experience"]))

    jobs = q.all()
    n = len(jobs)
    if n == 0:
        return {"matching_jobs": 0}

    job_ids = [j.id for j in jobs]
    skill_rows = db.query(JobSkill, Skill).join(Skill).filter(JobSkill.job_id.in_(job_ids)).all()
    skill_counts = Counter(s.normalized_name for _, s in skill_rows)

    salaries = [((j.salary_min or 0) + (j.salary_max or 0)) / 2 for j in jobs]
    exps = [((j.experience_min or 0) + (j.experience_max or 0)) / 2 for j in jobs]
    companies = Counter(j.company for j in jobs)
    locations = Counter(j.location for j in jobs)

    return {
        "matching_jobs": n,
        "top_skills": [{"skill": s, "count": c} for s, c in skill_counts.most_common(10)],
        "salary_stats": {
            "avg": round(sum(salaries) / n, 1),
            "min": round(min(salaries), 1),
            "max": round(max(salaries), 1),
        },
        "experience_stats": {
            "avg": round(sum(exps) / n, 1),
            "min": round(min(exps), 1),
            "max": round(max(exps), 1),
        },
        "location_distribution": locations.most_common(10),
        "company_distribution": companies.most_common(10),
    }
