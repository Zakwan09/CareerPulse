"""
Stage 1-2 of the pipeline: Data Ingestion + Schema Validation.

Reads the raw CSV (any row count), applies the configurable column mapping
from core.config.settings.COLUMN_MAP, validates required columns exist, and
writes an intermediate file: data/processed/01_ingested.csv

Run: python scripts/ingest_data.py [path/to/raw.csv]
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.app.core.config import settings  # noqa: E402

REQUIRED_COLUMNS = [
    "job_id", "job_title", "company", "location", "country",
    "experience_min", "experience_max", "salary_min", "salary_max",
    "currency", "employment_type", "work_mode", "industry",
    "job_description", "skills", "posted_date", "source",
]


def ingest(raw_path: Path) -> pd.DataFrame:
    if not raw_path.exists():
        raise FileNotFoundError(f"Raw data file not found: {raw_path}")

    df = pd.read_csv(raw_path)
    print(f"[ingest] Loaded {len(df)} rows from {raw_path.name}")

    # Apply configurable column mapping: rename source columns -> internal schema
    inverse_map = {v: k for k, v in settings.COLUMN_MAP.items()}
    df = df.rename(columns=inverse_map)

    # Schema validation: fail loudly & clearly if required columns are missing
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"[ingest] Schema validation failed. Missing required columns: {missing}. "
            f"Update COLUMN_MAP in backend/app/core/config.py if your source CSV "
            f"uses different column names."
        )

    print(f"[ingest] Schema validation passed. {len(df)} rows, {len(df.columns)} columns.")
    return df[REQUIRED_COLUMNS]


def main():
    raw_path = Path(sys.argv[1]) if len(sys.argv) > 1 else settings.RAW_DATA_PATH
    df = ingest(raw_path)

    settings.PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = settings.PROCESSED_DATA_DIR / "01_ingested.csv"
    df.to_csv(out_path, index=False)
    print(f"[ingest] Wrote {len(df)} rows -> {out_path}")


if __name__ == "__main__":
    main()
