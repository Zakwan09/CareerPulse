# CareerPulse — Data-Driven Job Market & Skill Intelligence Platform

CareerPulse analyzes job-posting data to answer: what skills are in demand,
which are growing, what they pay, and what a candidate is missing for a
target role. It's a real, runnable Data Science + NLP + ML + FastAPI
application — not a chatbot wrapper, not a static dashboard.

## Quickstart

```bash
cd CareerPulse
python -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r backend/requirements.txt

cp .env.example .env      # edit SECRET_KEY etc. if you like; SQLite works out of the box

python scripts/run_pipeline.py    # ingest -> clean -> extract skills -> store -> train models
python run.py                     # starts the server
```

Open **http://localhost:8000** — register an account, log in, and explore.

## What `run_pipeline.py` does

```
data/raw/jobs_demo.csv
        |
  ingest_data.py      -- column-mapping + schema validation
        |
  preprocess_data.py  -- cleaning, missing-value handling, dedup,
        |                text cleaning, skill extraction/normalization,
        |                feature engineering, load into DB
        v
   PostgreSQL / SQLite (jobs, skills, job_skills, users)
        |
  train_models.py     -- salary regression + role classifier -> models/*.pkl
```

The three stages can also be run individually:
`python scripts/ingest_data.py`, `python scripts/preprocess_data.py`,
`python scripts/train_models.py`.

**The FastAPI server never retrains models on startup or on request** — it
loads the saved `.pkl` files. If they're missing, ML endpoints return a
clear `503` telling you to run the training script, rather than fabricating
a prediction.

## Replacing the demo dataset

The pipeline is schema-driven and does not hard-code "100 rows" anywhere.
To use your own data:

1. Put your CSV at `data/raw/your_file.csv`.
2. If your column names differ from the internal schema, edit
   `COLUMN_MAP` in `backend/app/core/config.py` — no other code changes
   needed.
3. Run `python scripts/ingest_data.py data/raw/your_file.csv`, then
   `preprocess_data.py` and `train_models.py` as usual.

This works whether the file has 100 rows or 100,000.

## Database

Defaults to a local **SQLite** file (`data/processed/careerpulse.db`) so the
project runs with zero external setup. To use **PostgreSQL** instead (the
schema/ORM already targets it):

```bash
pip install "psycopg[binary]"
# in .env:
DATABASE_URL=postgresql+psycopg://postgres:password@localhost:5432/careerpulse
```

No application code changes are required either way — SQLAlchemy handles both.

## Project structure

```
CareerPulse/
├── backend/app/
│   ├── core/        # config, database, security (JWT + bcrypt)
│   ├── models/       # SQLAlchemy: User, Job, Skill, JobSkill
│   ├── schemas/       # Pydantic request/response models
│   ├── routers/        # auth, dashboard, jobs, skills, analytics, ml, forecast, skill_gap
│   ├── services/         # analytics, ml, forecast, skill_gap, auth logic
│   └── utils/              # skill_normalizer.py (taxonomy + alias dictionary + extraction)
├── frontend/
│   ├── templates/    # Jinja2 pages (login, register, dashboard, market, skills, trends, skill_gap, profile)
│   └── static/        # style.css, per-page JS (vanilla JS + fetch, Chart.js via CDN)
├── data/raw/            # jobs_demo.csv (100 synthetic postings)
├── data/processed/        # pipeline intermediate CSVs + SQLite DB (gitignored)
├── models/                  # trained salary_model.pkl, role_classifier.pkl (gitignored)
├── scripts/                  # ingest_data.py, preprocess_data.py, train_models.py, run_pipeline.py, generate_demo_data.py
└── run.py                      # starts uvicorn
```

## Key design choices & documented limitations

- **Skill extraction/normalization** (`backend/app/utils/skill_normalizer.py`):
  a canonical taxonomy + alias dictionary + phrase matching over both the
  structured `skills` column and free-text `job_description`. No external
  LLM API is used or required.
- **Salary prediction**: OneHot-encoded categoricals + multi-hot skill
  vector, compared Linear Regression (baseline) vs Random Forest; the
  better model (by MAE) is auto-selected and saved. On the 100-row demo
  set, Random Forest wins comfortably — expect this gap to change on a
  larger, real dataset.
- **Role classification**: TF-IDF + Logistic Regression, evaluated with
  accuracy/precision/recall/F1. `train_models.py` requires at least 5
  examples per class before training; with only ~5-15 examples per role in
  the 100-row demo set, accuracy is modest (~65%) — this is expected for a
  10-class problem at this data volume, and will improve with more data. If
  the class-count bar isn't met, a deterministic keyword-based fallback is
  used instead (never a silently fabricated prediction).
- **Forecasting**: aggregates postings by month per skill and fits a linear
  trend, evaluated against a naive moving-average baseline. Only 6 months
  of demo history exist, so forecasts are short (2 months ahead) and the
  in-sample evaluation is a documented limitation of the demo dataset size,
  not the architecture. If fewer than 3 months of history exist for a
  skill, the API returns an explicit `insufficient_data` status instead of
  a fabricated forecast.
- **Skill-gap weighted match score** and **learning-priority score**
  formulas are documented in-line in
  `backend/app/services/skill_gap_service.py` — both are fully
  data-driven (market demand, growth, salary association), never an LLM's
  arbitrary judgment.
- **Auth**: JWT bearer tokens, bcrypt password hashing via passlib,
  protected API routes via a FastAPI dependency. Frontend pages are static
  shells; a small JS guard (`requireAuth()`) redirects to `/login` if no
  token is present, and every API call attaches the token.

## API overview

See `/docs` (Swagger UI) once the server is running for the full,
interactive spec. Highlights:

```
POST /api/auth/register | /api/auth/login | /api/auth/logout | GET /api/auth/me
GET  /api/dashboard/summary
GET  /api/jobs | /api/jobs/{id}
GET  /api/market/overview            (filterable: role, location, industry, work_mode, employment_type, min_experience)
GET  /api/skills | /api/skills/{name} | /api/skills/{name}/trend
GET  /api/roles | /api/locations
POST /api/ml/predict-salary | POST /api/ml/classify-role
GET  /api/forecast/{skill_name}
POST /api/skill-gap/analyze
```

## Regenerating the demo dataset

`scripts/generate_demo_data.py` is a one-off script (not part of the
runtime pipeline) that produced `data/raw/jobs_demo.csv`. Re-run it if you
want a fresh random synthetic set (seeded, so it's reproducible by default).
