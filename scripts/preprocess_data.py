"""
Stages 3-9 of the pipeline:
  Data Cleaning -> Missing Value Handling -> Duplicate Removal ->
  Text Cleaning -> Skill Extraction -> Skill Normalization ->
  Feature Engineering -> Store in DB

Reads data/processed/01_ingested.csv (produced by ingest_data.py) and
loads clean, structured data into the `jobs`, `skills`, and `job_skills`
tables. Row count is never assumed -- works for 100 rows or 100,000.

Run: python scripts/preprocess_data.py
"""
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.app.core.config import settings                     # noqa: E402
from backend.app.core.database import SessionLocal, init_db       # noqa: E402
from backend.app.models.job import Job                             # noqa: E402
from backend.app.models.skill import Skill, JobSkill                # noqa: E402
from backend.app.utils.skill_normalizer import (                    # noqa: E402
    extract_skills, extract_skills_from_list, get_category,
)


def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def load_and_clean(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    n0 = len(df)

    # --- Missing value handling -----------------------------------------
    df["job_title"] = df["job_title"].fillna("Unknown Role")
    df["company"] = df["company"].fillna("Unknown Company")
    df["location"] = df["location"].fillna("Unspecified")
    df["country"] = df["country"].fillna("Unspecified")
    df["industry"] = df["industry"].fillna("Unspecified")
    df["employment_type"] = df["employment_type"].fillna("Full-time")
    df["work_mode"] = df["work_mode"].fillna("Onsite")
    df["currency"] = df["currency"].fillna("INR_LPA")
    df["source"] = df["source"].fillna("unknown")
    df["job_description"] = df["job_description"].fillna("")
    df["skills"] = df["skills"].fillna("")

    for col in ["experience_min", "experience_max", "salary_min", "salary_max"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    # impute numeric gaps with the column median (documented, simple strategy)
    for col in ["experience_min", "experience_max", "salary_min", "salary_max"]:
        median = df[col].median()
        n_missing = df[col].isna().sum()
        if n_missing:
            print(f"[clean] Imputing {n_missing} missing '{col}' values with median={median:.1f}")
        df[col] = df[col].fillna(median)

    df["posted_date"] = pd.to_datetime(df["posted_date"], errors="coerce")
    df = df.dropna(subset=["posted_date"])

    # --- Text cleaning -----------------------------------------------------
    df["job_description"] = df["job_description"].apply(clean_text)
    df["job_title"] = df["job_title"].apply(clean_text)

    # --- Duplicate detection/removal ---------------------------------------
    # 1) exact duplicate job_id
    df = df.drop_duplicates(subset=["job_id"], keep="first")
    # 2) content-level duplicates (same title+company+location+description)
    before = len(df)
    df = df.drop_duplicates(
        subset=["job_title", "company", "location", "job_description"], keep="first"
    )
    removed = before - len(df)
    if removed:
        print(f"[clean] Removed {removed} content-duplicate rows")

    print(f"[clean] {n0} raw rows -> {len(df)} clean rows")
    return df.reset_index(drop=True)


def extract_and_normalize_skills(row) -> list:
    """Combine the structured 'skills' column with skills mined from the
    free-text description, normalize, and de-duplicate."""
    from_list = extract_skills_from_list(row["skills"])
    from_text = extract_skills(row["job_description"])
    combined = list(dict.fromkeys(from_list + from_text))  # preserve order, dedupe
    return combined


def feature_engineer(df: pd.DataFrame) -> pd.DataFrame:
    df["experience_mid"] = (df["experience_min"] + df["experience_max"]) / 2
    df["salary_mid"] = (df["salary_min"] + df["salary_max"]) / 2
    df["extracted_skills"] = df.apply(extract_and_normalize_skills, axis=1)
    df["skill_count"] = df["extracted_skills"].apply(len)
    df["posting_month"] = df["posted_date"].dt.to_period("M").astype(str)
    return df


def store_in_db(df: pd.DataFrame):
    init_db()
    db = SessionLocal()
    try:
        # wipe existing demo data for a clean re-run (idempotent pipeline)
        db.query(JobSkill).delete()
        db.query(Job).delete()
        db.query(Skill).delete()
        db.commit()

        skill_cache = {}  # normalized_name -> Skill row

        def get_or_create_skill(name: str) -> Skill:
            if name in skill_cache:
                return skill_cache[name]
            existing = db.query(Skill).filter(Skill.normalized_name == name).first()
            if existing:
                skill_cache[name] = existing
                return existing
            s = Skill(skill_name=name, normalized_name=name, category=get_category(name))
            db.add(s)
            db.flush()
            skill_cache[name] = s
            return s

        for _, row in df.iterrows():
            job = Job(
                external_job_id=str(row["job_id"]),
                job_title=row["job_title"],
                company=row["company"],
                location=row["location"],
                country=row["country"],
                experience_min=float(row["experience_min"]),
                experience_max=float(row["experience_max"]),
                salary_min=float(row["salary_min"]),
                salary_max=float(row["salary_max"]),
                currency=row["currency"],
                employment_type=row["employment_type"],
                work_mode=row["work_mode"],
                industry=row["industry"],
                job_description=row["job_description"],
                posted_date=row["posted_date"].date(),
                source=row["source"],
            )
            db.add(job)
            db.flush()  # get job.id

            for skill_name in row["extracted_skills"]:
                skill = get_or_create_skill(skill_name)
                db.add(JobSkill(job_id=job.id, skill_id=skill.id))

        db.commit()
        n_jobs = db.query(Job).count()
        n_skills = db.query(Skill).count()
        n_links = db.query(JobSkill).count()
        print(f"[store] Loaded {n_jobs} jobs, {n_skills} distinct skills, {n_links} job-skill links")
    finally:
        db.close()


def main():
    ingested_path = settings.PROCESSED_DATA_DIR / "01_ingested.csv"
    if not ingested_path.exists():
        raise FileNotFoundError(
            f"{ingested_path} not found. Run scripts/ingest_data.py first."
        )

    df = load_and_clean(ingested_path)
    df = feature_engineer(df)

    out_path = settings.PROCESSED_DATA_DIR / "02_processed.csv"
    df.drop(columns=["extracted_skills"]).to_csv(out_path, index=False)
    print(f"[preprocess] Wrote {len(df)} rows -> {out_path}")

    store_in_db(df)


if __name__ == "__main__":
    main()
