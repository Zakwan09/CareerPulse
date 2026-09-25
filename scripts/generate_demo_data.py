"""
Generates data/raw/jobs_demo.csv -- 100 realistic synthetic job postings.
Run once: python scripts/generate_demo_data.py
This is NOT part of the runtime pipeline; it only creates the seed CSV.
"""
import csv
import random
import uuid
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "raw" / "jobs_demo.csv"

ROLES = [
    "Data Scientist", "Data Analyst", "Data Engineer", "Machine Learning Engineer",
    "AI Engineer", "ML Engineer", "Software Engineer", "Python Developer",
    "Business Analyst", "BI Analyst",
]

# Skill pools per role (used to build realistic descriptions + skills column)
ROLE_SKILLS = {
    "Data Scientist": ["Python", "Pandas", "NumPy", "Scikit-learn", "SQL", "Machine Learning",
                        "Statistics", "Power BI", "TensorFlow", "AWS"],
    "Data Analyst": ["SQL", "Excel", "Power BI", "Python", "Pandas", "Tableau",
                      "Data Visualization", "Statistics", "PostgreSQL"],
    "Data Engineer": ["Python", "SQL", "Spark", "Airflow", "AWS", "ETL", "PostgreSQL",
                       "Docker", "Kafka", "Big Data"],
    "Machine Learning Engineer": ["Python", "Machine Learning", "TensorFlow", "PyTorch",
                                   "Docker", "AWS", "SQL", "MLOps", "Scikit-learn"],
    "AI Engineer": ["Python", "Machine Learning", "Artificial Intelligence", "TensorFlow",
                     "PyTorch", "NLP", "Docker", "AWS"],
    "ML Engineer": ["Python", "Machine Learning", "Scikit-learn", "Docker", "AWS",
                     "SQL", "PyTorch", "MLOps"],
    "Software Engineer": ["Python", "Java", "SQL", "Git", "Docker", "REST APIs",
                           "FastAPI", "AWS"],
    "Python Developer": ["Python", "FastAPI", "Django", "SQL", "REST APIs", "Docker",
                          "PostgreSQL", "Git"],
    "Business Analyst": ["SQL", "Excel", "Power BI", "Data Visualization", "Statistics",
                          "Tableau", "Business Intelligence"],
    "BI Analyst": ["Power BI", "SQL", "Tableau", "Excel", "Data Visualization",
                    "ETL", "Statistics"],
}

COMPANIES = [
    "InfosysNext", "TCS Digital", "Wipro Analytics", "Persistent Systems", "Zensar Tech",
    "Mindtree Labs", "Capgemini India", "Accenture Data", "Cognizant Insights", "HCL Tech",
    "Flipkart", "Swiggy", "Zomato", "Razorpay", "PhonePe", "CRED", "Freshworks",
    "Zoho", "Byju's", "PolicyBazaar", "Nykaa", "Paytm", "MakeMyTrip", "Ola Cabs",
    "Tata Elxsi", "L&T Infotech", "Mphasis", "Hexaware", "Sonata Software", "Quantiphi",
]

LOCATIONS = [
    ("Pune", "India"), ("Mumbai", "India"), ("Bengaluru", "India"), ("Hyderabad", "India"),
    ("Chennai", "India"), ("Gurugram", "India"), ("Noida", "India"), ("Kolkata", "India"),
    ("Remote", "India"), ("Ahmedabad", "India"),
]

INDUSTRIES = ["IT Services", "FinTech", "E-commerce", "EdTech", "Healthcare Tech",
              "Consulting", "SaaS", "Logistics Tech", "Travel Tech", "Retail Tech"]

EMPLOYMENT_TYPES = ["Full-time", "Contract", "Internship"]
WORK_MODES = ["Onsite", "Remote", "Hybrid"]
EXP_BANDS = [(0, 1), (0, 2), (1, 3), (2, 4), (3, 5), (4, 7), (5, 8), (6, 10)]

DESC_TEMPLATES = [
    "We are looking for a {role} to join our growing analytics team in {location}. "
    "The ideal candidate has experience with {skills}. Responsibilities include working "
    "with large datasets, building models, and collaborating with cross-functional teams.",
    "{company} is hiring a {role} with {exp_min}-{exp_max} years of experience. "
    "Required skills: {skills}. Knowledge of {extra} is a strong plus. "
    "You will work on real business problems in the {industry} domain.",
    "Join {company} as a {role}! We need someone proficient in {skills}. "
    "This role is {work_mode} and based in {location}. Prior exposure to {extra} preferred.",
    "Exciting opportunity for a {role} at {company}. Must have hands-on experience with "
    "{skills}. Familiarity with {extra} is beneficial. {exp_min}-{exp_max} years experience required.",
]


def month_range_dates(n):
    """Spread postings across the last 6 months with an increasing skew (simulates growth)."""
    today = date(2026, 9, 25)
    dates = []
    weights = [1, 1, 2, 2, 3, 4]  # older -> newer, more recent months get more postings
    months_back = list(range(5, -1, -1))
    pool = []
    for mb, w in zip(months_back, weights):
        pool += [mb] * w
    for _ in range(n):
        mb = random.choice(pool)
        d = today.replace(day=1) - timedelta(days=mb * 30)
        day_offset = random.randint(0, 27)
        dates.append(d + timedelta(days=day_offset))
    return dates


def build_row(i, posted_date):
    role = random.choice(ROLES)
    company = random.choice(COMPANIES)
    location, country = random.choice(LOCATIONS)
    industry = random.choice(INDUSTRIES)
    employment_type = random.choices(EMPLOYMENT_TYPES, weights=[8, 1.5, 0.5])[0]
    work_mode = random.choice(WORK_MODES)
    exp_min, exp_max = random.choice(EXP_BANDS)

    base_pool = ROLE_SKILLS[role]
    n_skills = random.randint(4, 7)
    chosen = random.sample(base_pool, min(n_skills, len(base_pool)))
    extra_pool = [s for s in sum(ROLE_SKILLS.values(), []) if s not in chosen]
    extra = random.sample(extra_pool, 2)

    # salary scales roughly with experience + a role multiplier, in INR lakhs/year
    role_mult = {
        "Data Scientist": 1.3, "Machine Learning Engineer": 1.35, "AI Engineer": 1.4,
        "ML Engineer": 1.3, "Data Engineer": 1.2, "Software Engineer": 1.1,
        "Python Developer": 1.0, "Data Analyst": 0.9, "Business Analyst": 0.85,
        "BI Analyst": 0.85,
    }[role]
    base = 4 + exp_min * 2.2
    salary_min = round(base * role_mult, 1)
    salary_max = round(salary_min + 3 + exp_max * 0.8, 1)

    template = random.choice(DESC_TEMPLATES)
    desc = template.format(
        role=role, company=company, location=location, industry=industry,
        work_mode=work_mode.lower(), exp_min=exp_min, exp_max=exp_max,
        skills=", ".join(chosen), extra=", ".join(extra),
    )

    return {
        "job_id": f"JOB{i:04d}",
        "job_title": role,
        "company": company,
        "location": location,
        "country": country,
        "experience_min": exp_min,
        "experience_max": exp_max,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "currency": "INR_LPA",
        "employment_type": employment_type,
        "work_mode": work_mode,
        "industry": industry,
        "job_description": desc,
        "skills": "; ".join(chosen),
        "posted_date": posted_date.isoformat(),
        "source": "careerpulse_demo",
    }


def main():
    n = 100
    dates = sorted(month_range_dates(n))
    rows = [build_row(i + 1, dates[i]) for i in range(n)]
    # small deliberate messiness for pipeline to clean: a couple dup-ish rows, one missing salary
    rows[37]["salary_min"] = ""
    rows[37]["salary_max"] = ""
    dup = dict(rows[10])
    dup["job_id"] = "JOB0011DUP"
    rows.append(dup)  # exact duplicate content, different id -> tests dedup on content

    fieldnames = list(rows[0].keys())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
