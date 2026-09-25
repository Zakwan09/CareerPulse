"""
Runs the complete pipeline end to end:
  ingest -> preprocess (clean, dedupe, extract/normalize skills, store in DB) -> train models

Run: python scripts/run_pipeline.py
"""
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent


def run(script: str):
    print(f"\n{'=' * 60}\nRunning {script}\n{'=' * 60}")
    result = subprocess.run([sys.executable, str(SCRIPTS_DIR / script)])
    if result.returncode != 0:
        print(f"[run_pipeline] {script} failed. Stopping.")
        sys.exit(result.returncode)


def main():
    run("ingest_data.py")
    run("preprocess_data.py")
    run("train_models.py")
    print("\nPipeline complete. Start the app with: python run.py")


if __name__ == "__main__":
    main()
