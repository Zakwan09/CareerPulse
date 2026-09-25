"""
skill_normalizer.py

Single source of truth for:
  1. The canonical skill vocabulary (SKILL_TAXONOMY)
  2. Alias -> canonical-name mapping (ALIASES)
  3. normalize_skill(): map any raw string to its canonical form
  4. extract_skills(): phrase-match skills out of free text (job descriptions)

No routes or services should hard-code skill strings; they should always
go through this module so behaviour stays consistent app-wide.
"""
import re
from typing import List, Set

# ---------------------------------------------------------------------
# 1. Canonical skill -> category (the taxonomy)
# ---------------------------------------------------------------------
SKILL_TAXONOMY = {
    "Python": "Programming",
    "Java": "Programming",
    "JavaScript": "Programming",
    "R": "Programming",
    "C++": "Programming",

    "SQL": "Database",
    "PostgreSQL": "Database",
    "MySQL": "Database",
    "MongoDB": "Database",

    "AWS": "Cloud",
    "Azure": "Cloud",
    "GCP": "Cloud",

    "Spark": "Big Data",
    "PySpark": "Big Data",
    "Hadoop": "Big Data",
    "Kafka": "Big Data",

    "Airflow": "Data Engineering",
    "ETL": "Data Engineering",

    "Pandas": "Data Science",
    "NumPy": "Data Science",
    "Statistics": "Data Science",

    "Machine Learning": "Machine Learning",
    "Scikit-learn": "Machine Learning",
    "MLOps": "Machine Learning",

    "TensorFlow": "AI",
    "PyTorch": "AI",
    "Artificial Intelligence": "AI",
    "NLP": "AI",
    "Deep Learning": "AI",

    "Power BI": "Visualization",
    "Tableau": "Visualization",
    "Data Visualization": "Visualization",
    "Excel": "Visualization",
    "Business Intelligence": "Visualization",

    "Docker": "DevOps",
    "Kubernetes": "DevOps",
    "Git": "DevOps",
    "CI/CD": "DevOps",

    "FastAPI": "Web Development",
    "Django": "Web Development",
    "REST APIs": "Web Development",
    "Flask": "Web Development",
}

# ---------------------------------------------------------------------
# 2. Alias map: raw/variant text (lower-cased) -> canonical name
# ---------------------------------------------------------------------
ALIASES = {
    # Cloud
    "amazon web services": "AWS", "aws cloud": "AWS", "amazon aws": "AWS", "aws": "AWS",
    "microsoft azure": "Azure", "azure": "Azure",
    "google cloud": "GCP", "google cloud platform": "GCP", "gcp": "GCP",

    # Database
    "postgres": "PostgreSQL", "postgresql database": "PostgreSQL", "postgresql": "PostgreSQL",
    "mysql": "MySQL", "mongo": "MongoDB", "mongodb": "MongoDB",
    "sql": "SQL", "structured query language": "SQL",

    # ML / AI
    "machine learning": "Machine Learning", "ml": "Machine Learning",
    "artificial intelligence": "Artificial Intelligence", "ai": "Artificial Intelligence",
    "deep learning": "Deep Learning", "dl": "Deep Learning",
    "scikit-learn": "Scikit-learn", "sklearn": "Scikit-learn", "scikit learn": "Scikit-learn",
    "tensorflow": "TensorFlow", "tf": "TensorFlow",
    "pytorch": "PyTorch",
    "nlp": "NLP", "natural language processing": "NLP",
    "mlops": "MLOps",

    # Visualization
    "powerbi": "Power BI", "power bi desktop": "Power BI", "power bi": "Power BI",
    "tableau": "Tableau",
    "excel": "Excel", "ms excel": "Excel", "microsoft excel": "Excel",
    "data viz": "Data Visualization", "data visualization": "Data Visualization",
    "bi": "Business Intelligence", "business intelligence": "Business Intelligence",

    # Data engineering / big data
    "pyspark": "PySpark", "apache spark": "Spark", "spark": "Spark",
    "hadoop": "Hadoop", "kafka": "Kafka", "apache kafka": "Kafka",
    "airflow": "Airflow", "apache airflow": "Airflow",
    "etl": "ETL", "extract transform load": "ETL",

    # Data science
    "pandas": "Pandas", "numpy": "NumPy", "statistics": "Statistics", "stats": "Statistics",

    # DevOps
    "docker": "Docker", "kubernetes": "Kubernetes", "k8s": "Kubernetes",
    "git": "Git", "github": "Git", "ci/cd": "CI/CD", "cicd": "CI/CD",

    # Web dev
    "fastapi": "FastAPI", "django": "Django", "flask": "Flask",
    "rest api": "REST APIs", "rest apis": "REST APIs", "restful apis": "REST APIs",

    # Programming
    "python": "Python", "java": "Java", "javascript": "JavaScript", "js": "JavaScript",
    "c++": "C++", "r language": "R", " r ": "R",
}

# Build the phrase-matching list: every canonical skill + every alias,
# longest phrase first so e.g. "Power BI Desktop" matches before "BI".
_ALL_PHRASES = sorted(
    set(list(SKILL_TAXONOMY.keys()) + list(ALIASES.keys())),
    key=len,
    reverse=True,
)


def normalize_skill(raw: str) -> str:
    """Map a raw skill string to its canonical form. Unknown skills are
    title-cased and returned as-is so nothing is silently dropped."""
    key = raw.strip().lower()
    if key in ALIASES:
        return ALIASES[key]
    if raw.strip() in SKILL_TAXONOMY:
        return raw.strip()
    # try a case-insensitive match against canonical names
    for canon in SKILL_TAXONOMY:
        if canon.lower() == key:
            return canon
    return raw.strip()


def get_category(canonical_skill: str) -> str:
    return SKILL_TAXONOMY.get(canonical_skill, "Other")


def extract_skills(text: str) -> List[str]:
    """
    Phrase-match skills out of free text (e.g. a job description).
    Case-insensitive, alias-aware, de-duplicated, returns canonical names.
    """
    if not text:
        return []
    lowered = f" {text.lower()} "
    found: Set[str] = set()

    for phrase in _ALL_PHRASES:
        p = phrase.lower().strip()
        if not p:
            continue
        # word-boundary match to avoid partial hits (e.g. "r" inside "learn")
        pattern = r"(?<![a-zA-Z0-9+])" + re.escape(p) + r"(?![a-zA-Z0-9+])"
        if re.search(pattern, lowered):
            found.add(normalize_skill(phrase))

    return sorted(found)


def extract_skills_from_list(skills_field: str) -> List[str]:
    """
    For a structured 'skills' CSV column like 'Python; SQL; AWS',
    split on common delimiters and normalize each token.
    """
    if not skills_field:
        return []
    tokens = re.split(r"[;,|/]", str(skills_field))
    out = []
    for t in tokens:
        t = t.strip()
        if t:
            out.append(normalize_skill(t))
    # de-dupe while preserving order
    seen = set()
    result = []
    for s in out:
        if s not in seen:
            seen.add(s)
            result.append(s)
    return result
