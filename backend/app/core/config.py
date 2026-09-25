"""
Central configuration loaded from environment variables (.env).
Nothing here should ever be hard-coded with real secrets.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[3]  # project root (CareerPulse/)
load_dotenv(ROOT_DIR / ".env")


class Settings:
    # --- Database -----------------------------------------------------
    # Primary target is PostgreSQL. If DATABASE_URL is not set (e.g. no
    # Postgres server available locally), we fall back to a local SQLite
    # file so the project still runs out of the box. Swap DATABASE_URL in
    # .env to point at Postgres for production use -- no code changes needed.
    DATABASE_URL: str = os.getenv("DATABASE_URL") or (
        f"sqlite:///{ROOT_DIR / 'data' / 'processed' / 'careerpulse.db'}"
    )

    # --- Auth ------------------------------------------------------------
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-only-change-this-secret")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    # --- Paths -------------------------------------------------------------
    RAW_DATA_PATH: Path = ROOT_DIR / "data" / "raw" / "jobs_demo.csv"
    PROCESSED_DATA_DIR: Path = ROOT_DIR / "data" / "processed"
    MODELS_DIR: Path = ROOT_DIR / "models"
    SALARY_MODEL_PATH: Path = MODELS_DIR / "salary_model.pkl"
    ROLE_MODEL_PATH: Path = MODELS_DIR / "role_classifier.pkl"

    # --- Column mapping (for future dataset replacement) -----------------
    # If a new raw CSV uses different column names, map them here instead
    # of changing code throughout the app.
    COLUMN_MAP: dict = {
        "job_id": "job_id",
        "job_title": "job_title",
        "company": "company",
        "location": "location",
        "country": "country",
        "experience_min": "experience_min",
        "experience_max": "experience_max",
        "salary_min": "salary_min",
        "salary_max": "salary_max",
        "currency": "currency",
        "employment_type": "employment_type",
        "work_mode": "work_mode",
        "industry": "industry",
        "job_description": "job_description",
        "skills": "skills",
        "posted_date": "posted_date",
        "source": "source",
    }


settings = Settings()
