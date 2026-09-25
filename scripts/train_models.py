"""
Trains and saves:
  1. models/salary_model.pkl   -- salary regression (baseline + stronger model, best kept)
  2. models/role_classifier.pkl -- TF-IDF + Logistic Regression role classifier
                                    (only trained if enough examples per class exist)

Run AFTER scripts/preprocess_data.py (needs the populated database).
Run: python scripts/train_models.py
"""
import sys
import pickle
from pathlib import Path
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    accuracy_score, precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, MultiLabelBinarizer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.app.core.config import settings          # noqa: E402
from backend.app.core.database import SessionLocal      # noqa: E402
from backend.app.models.job import Job                   # noqa: E402
from backend.app.models.skill import Skill, JobSkill       # noqa: E402

MIN_EXAMPLES_PER_CLASS = 5  # role classifier only trains if every class clears this bar


def load_training_frame() -> pd.DataFrame:
    db = SessionLocal()
    try:
        jobs = db.query(Job).all()
        rows = []
        for j in jobs:
            skill_names = [
                s.normalized_name for s in
                db.query(Skill).join(JobSkill).filter(JobSkill.job_id == j.id).all()
            ]
            rows.append({
                "job_title": j.job_title,
                "location": j.location,
                "industry": j.industry,
                "work_mode": j.work_mode,
                "employment_type": j.employment_type,
                "experience_mid": ((j.experience_min or 0) + (j.experience_max or 0)) / 2,
                "salary_mid": ((j.salary_min or 0) + (j.salary_max or 0)) / 2,
                "skills": skill_names,
                "job_description": j.job_description,
            })
        return pd.DataFrame(rows)
    finally:
        db.close()


# ------------------------------------------------------------------
# Model 1: Salary prediction
# ------------------------------------------------------------------
def train_salary_model(df: pd.DataFrame):
    print("\n=== Training salary prediction model ===")

    mlb = MultiLabelBinarizer()
    skill_matrix = mlb.fit_transform(df["skills"])
    skill_df = pd.DataFrame(skill_matrix, columns=[f"skill_{s}" for s in mlb.classes_])

    cat_cols = ["job_title", "location", "industry", "work_mode", "employment_type"]
    num_cols = ["experience_mid"]

    X = pd.concat([df[cat_cols + num_cols].reset_index(drop=True), skill_df], axis=1)
    y = df["salary_mid"].values

    preprocess = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols),
        ],
        remainder="passthrough",  # numeric + skill dummy columns pass through
    )

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    results = {}
    for name, model in [
        ("LinearRegression", LinearRegression()),
        ("RandomForest", RandomForestRegressor(n_estimators=200, random_state=42, max_depth=8)),
    ]:
        pipe = Pipeline([("prep", preprocess), ("model", model)])
        pipe.fit(X_train, y_train)
        preds = pipe.predict(X_test)
        mae = mean_absolute_error(y_test, preds)
        rmse = mean_squared_error(y_test, preds) ** 0.5
        r2 = r2_score(y_test, preds)
        results[name] = {"pipeline": pipe, "mae": mae, "rmse": rmse, "r2": r2}
        print(f"  {name:20s}  MAE={mae:.2f}  RMSE={rmse:.2f}  R2={r2:.3f}")

    best_name = min(results, key=lambda k: results[k]["mae"])
    best = results[best_name]
    print(f"  -> Selected best model: {best_name}")

    bundle = {
        "pipeline": best["pipeline"],
        "mlb": mlb,
        "cat_cols": cat_cols,
        "num_cols": num_cols,
        "model_name": best_name,
        "metrics": {"mae": best["mae"], "rmse": best["rmse"], "r2": best["r2"]},
    }
    settings.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    with open(settings.SALARY_MODEL_PATH, "wb") as f:
        pickle.dump(bundle, f)
    print(f"  Saved -> {settings.SALARY_MODEL_PATH}")


# ------------------------------------------------------------------
# Model 2: Role classification (with deterministic fallback)
# ------------------------------------------------------------------
def train_role_classifier(df: pd.DataFrame):
    print("\n=== Training role classifier ===")
    class_counts = Counter(df["job_title"])
    min_count = min(class_counts.values()) if class_counts else 0
    print(f"  Class distribution: {dict(class_counts)}")

    if min_count < MIN_EXAMPLES_PER_CLASS or len(class_counts) < 2:
        print(
            f"  Not enough examples per class (min={min_count}, need >= "
            f"{MIN_EXAMPLES_PER_CLASS}). Skipping ML classifier training; "
            f"the app will use a deterministic keyword-based fallback instead "
            f"(see backend/app/services/ml_service.py)."
        )
        bundle = {"trained": False, "reason": "insufficient examples per class"}
        with open(settings.ROLE_MODEL_PATH, "wb") as f:
            pickle.dump(bundle, f)
        return

    X_train, X_test, y_train, y_test = train_test_split(
        df["job_description"], df["job_title"], test_size=0.2, random_state=42,
        stratify=df["job_title"],
    )

    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(max_features=2000, ngram_range=(1, 2), stop_words="english")),
        ("clf", LogisticRegression(max_iter=1000)),
    ])
    pipe.fit(X_train, y_train)
    preds = pipe.predict(X_test)

    acc = accuracy_score(y_test, preds)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, preds, average="weighted", zero_division=0
    )
    print(f"  Accuracy={acc:.3f}  Precision={precision:.3f}  Recall={recall:.3f}  F1={f1:.3f}")

    bundle = {
        "trained": True,
        "pipeline": pipe,
        "metrics": {"accuracy": acc, "precision": precision, "recall": recall, "f1": f1},
        "classes": sorted(class_counts.keys()),
    }
    with open(settings.ROLE_MODEL_PATH, "wb") as f:
        pickle.dump(bundle, f)
    print(f"  Saved -> {settings.ROLE_MODEL_PATH}")


def main():
    df = load_training_frame()
    if df.empty:
        raise RuntimeError(
            "No data found in the database. Run scripts/ingest_data.py and "
            "scripts/preprocess_data.py first."
        )
    train_salary_model(df)
    train_role_classifier(df)
    print("\nTraining complete.")


if __name__ == "__main__":
    main()
