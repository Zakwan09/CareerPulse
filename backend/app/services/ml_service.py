"""
Loads trained model files (does NOT retrain on every request). Raises a
clear error if a model file is missing, and never fabricates a prediction.
"""
import pickle
from functools import lru_cache

import pandas as pd

from backend.app.core.config import settings
from backend.app.utils.skill_normalizer import extract_skills, normalize_skill

# Deterministic keyword fallback used only if the ML role classifier
# was not trained (insufficient examples per class -- see train_models.py)
ROLE_KEYWORDS = {
    "Data Scientist": ["data scientist", "data science"],
    "Data Analyst": ["data analyst", "data analysis"],
    "Data Engineer": ["data engineer", "etl", "airflow", "pipeline"],
    "Machine Learning Engineer": ["machine learning engineer"],
    "AI Engineer": ["ai engineer", "artificial intelligence engineer"],
    "ML Engineer": ["ml engineer"],
    "Software Engineer": ["software engineer", "software developer"],
    "Python Developer": ["python developer"],
    "Business Analyst": ["business analyst"],
    "BI Analyst": ["bi analyst", "business intelligence analyst"],
}


@lru_cache(maxsize=1)
def _load_salary_bundle():
    if not settings.SALARY_MODEL_PATH.exists():
        raise FileNotFoundError(
            "Salary model not found. Run `python scripts/train_models.py` first."
        )
    with open(settings.SALARY_MODEL_PATH, "rb") as f:
        return pickle.load(f)


@lru_cache(maxsize=1)
def _load_role_bundle():
    if not settings.ROLE_MODEL_PATH.exists():
        raise FileNotFoundError(
            "Role classifier artifact not found. Run `python scripts/train_models.py` first."
        )
    with open(settings.ROLE_MODEL_PATH, "rb") as f:
        return pickle.load(f)


def predict_salary(job_title: str, location: str, experience: float,
                    industry: str = None, work_mode: str = None,
                    skills: list[str] = None) -> dict:
    bundle = _load_salary_bundle()
    pipe = bundle["pipeline"]
    mlb = bundle["mlb"]

    norm_skills = [normalize_skill(s) for s in (skills or [])]
    skill_row = {f"skill_{c}": (1 if c in norm_skills else 0) for c in mlb.classes_}

    row = {
        "job_title": job_title,
        "location": location,
        "industry": industry or "Unspecified",
        "work_mode": work_mode or "Onsite",
        "employment_type": "Full-time",
        "experience_mid": experience,
        **skill_row,
    }
    X = pd.DataFrame([row])
    pred = float(pipe.predict(X)[0])
    return {"predicted_salary_lpa": round(pred, 2), "model_used": bundle["model_name"]}


def classify_role(job_description: str) -> dict:
    bundle = _load_role_bundle()
    if bundle.get("trained"):
        pipe = bundle["pipeline"]
        pred = pipe.predict([job_description])[0]
        proba = pipe.predict_proba([job_description]).max()
        return {"predicted_role": pred, "confidence": round(float(proba), 3), "method": "ml_tfidf_logreg"}

    # deterministic fallback
    text = job_description.lower()
    scores = {role: sum(1 for kw in kws if kw in text) for role, kws in ROLE_KEYWORDS.items()}
    best_role = max(scores, key=scores.get)
    if scores[best_role] == 0:
        return {"predicted_role": "Unclassified", "confidence": None, "method": "keyword_fallback"}
    return {"predicted_role": best_role, "confidence": None, "method": "keyword_fallback"}
