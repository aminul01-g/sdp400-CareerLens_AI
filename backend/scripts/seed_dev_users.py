"""Create demo users with realistic, hand-written profiles for manual QA.

Run:  python -m scripts.seed_dev_users

**These are synthetic profiles, not real people.** Every skill, project and
qualification is written by hand here. That matters for two reasons: proposal
section 7.3 requires that only consented or anonymised samples are used, and
harvesting real CVs would put other people's data in the repository.

The profiles are deliberately imperfect — a user missing some of a role's
requirements, a backend-leaning engineer, a sparse profile — because a demo where
every profile matches at 95% tests nothing. The same consideration applies to the
evaluation dataset in ``app/ml/evaluation/labelled_profiles.jsonl``.

Idempotent: keyed on email, so re-running updates rather than duplicates.

The demo addresses use a ``.dev`` domain, not ``.local``. These rows are written
straight to the database, so nothing validates them here — but the login endpoint
does, and ``.local`` is reserved by RFC 6762 for mDNS, so a ``.local`` account
would be created successfully and then be unable to log in.
"""

from __future__ import annotations

import logging
import sys
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import session_scope
from app.models.education import Certification, EducationRecord
from app.models.profile import Profile
from app.models.project import Project
from app.models.skill import Skill
from app.models.user import User, UserRole
from app.models.user_skill import SkillSource, UserSkill

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("seed_dev_users")

DEMO_PASSWORD = "Demo#Pass2026"

DEMO_USERS: list[dict] = [
    {
        "email": "ml.engineer@careerlens.dev",
        "name": "Nusrat Jahan",
        "headline": "Machine Learning Engineer",
        "career_goal": "Move from model development into production MLOps work.",
        "bio": "Final-year computer science undergraduate with two research internships in "
               "applied computer vision.",
        "location": "Dhaka, Bangladesh",
        "education_level": "Undergraduate",
        "years_experience": 2,
        "preferred_role_family": "ML Engineer",
        "links": {"github": "https://github.com/example-ml-engineer"},
        "skills": {
            "python": 5, "scikit-learn": 4, "pytorch": 4, "pandas": 4, "numpy": 4,
            "sql": 4, "machine-learning": 5, "deep-learning": 3, "neural-networks": 3,
            "convolutional-neural-networks": 3, "statistics": 4, "docker": 3,
            "git": 4, "linear-algebra": 3, "feature-engineering": 3,
            "cross-validation": 4, "model-selection": 3, "data-cleaning": 4,
        },
        "projects": [
            {
                "title": "Plant disease classifier",
                "description": "Trained a convolutional neural network on 12,000 leaf images to "
                               "classify disease across nine crop species, deployed behind a "
                               "FastAPI service.",
                "tech_stack": ["python", "pytorch", "convolutional-neural-networks",
                               "computer-vision", "fastapi", "docker"],
                "role": "Solo developer",
            },
            {
                "title": "Sentiment analysis pipeline",
                "description": "Built an ETL pipeline with scikit-learn and pandas that scores "
                               "product reviews, with model evaluation via cross-validation.",
                "tech_stack": ["python", "scikit-learn", "pandas", "nltk", "sql"],
                "role": "Solo developer",
            },
        ],
        "education": [
            {
                "institution": "Example University of Engineering and Technology",
                "degree": "BSc",
                "field_of_study": "Computer Science and Engineering",
                "start_year": 2021,
                "end_year": 2025,
                "grade": "First Class",
            }
        ],
        "certifications": [
            {"name": "Deep Learning Specialization", "issuer": "Example Online University",
             "issued_on": date(2024, 6, 1)}
        ],
    },
    {
        "email": "data.scientist@careerlens.dev",
        "name": "Tanvir Hasan",
        "headline": "Data Scientist focused on experimentation",
        "career_goal": "Move into a senior data science role leading experimentation.",
        "bio": "Data scientist with three years in product analytics, comfortable designing "
               "experiments and reading them honestly.",
        "location": "Chattogram, Bangladesh",
        "education_level": "Master",
        "years_experience": 3,
        "preferred_role_family": "Data Science",
        "links": {"linkedin": "https://linkedin.com/in/example-ds"},
        "skills": {
            "python": 4, "sql": 5, "pandas": 5, "numpy": 4, "statistics": 5,
            "a-b-testing": 4, "hypothesis-testing": 4, "regression-analysis": 4,
            "scikit-learn": 4, "data-visualization": 4, "data-cleaning": 4,
            "tableau": 3, "power-bi": 3, "experimentation": 4, "machine-learning": 3,
            "feature-engineering": 3, "time-series-analysis": 3, "excel": 4,
            "technical-writing": 4, "data-storytelling": 4,
        },
        "projects": [
            {
                "title": "Pricing experiment analysis",
                "description": "Designed and analysed a two-week pricing A/B test across 40,000 "
                               "users, including a pre-registered stopping rule and a "
                               "sequential-error-corrected significance test.",
                "tech_stack": ["python", "sql", "pandas", "a-b-testing", "hypothesis-testing",
                               "regression-analysis"],
                "role": "Experiment owner",
            },
            {
                "title": "Churn prediction model",
                "description": "Built and validated a gradient-boosted churn model, reporting "
                               "calibration and lift alongside accuracy and documenting the "
                               "known limitations of the training window.",
                "tech_stack": ["python", "scikit-learn", "xgboost", "postgresql"],
                "role": "Modelling lead",
            },
        ],
        "education": [
            {
                "institution": "Example Institute of Business and Economics",
                "degree": "MSc",
                "field_of_study": "Data Science",
                "start_year": 2019,
                "end_year": 2021,
                "grade": "3.85/4.00",
            }
        ],
        "certifications": [
            {"name": "Certified Data Analyst", "issuer": "Example Analytics Institute",
             "issued_on": date(2022, 3, 15), "expires_on": date(2027, 3, 15)}
        ],
    },
    {
        "email": "mlops.engineer@careerlens.dev",
        "name": "Farhan Kabir",
        "headline": "MLOps Engineer",
        "career_goal": "Own a production ML platform end to end.",
        "bio": "Infrastructure engineer who moved into MLOps; spends most of her time on "
               "deployment pipelines, observability and cost.",
        "location": "Sylhet, Bangladesh",
        "education_level": "Undergraduate",
        "years_experience": 4,
        "preferred_role_family": "MLOps",
        "links": {"github": "https://github.com/example-mlops", "portfolio": "https://example.dev"},
        "skills": {
            "python": 5, "docker": 5, "kubernetes": 4, "ci-cd": 4, "mlops": 4,
            "mlflow": 4, "aws": 4, "terraform": 3,
            "prometheus": 3, "grafana": 3, "observability": 3, "linux": 5, "bash": 5, "git": 4,
            "fastapi": 4, "rest-apis": 4, "machine-learning": 3, "scikit-learn": 3,
            "pytorch": 2, "testing": 3, "regularization": 2,
        },
        "projects": [
            {
                "title": "Model deployment platform",
                "description": "Built a CI/CD platform that trains, evaluates and promotes models "
                               "to Kubernetes with automated rollback, using MLflow for "
                               "experiment tracking and Prometheus for serving metrics.",
                "tech_stack": ["python", "docker", "kubernetes", "ci-cd", "mlflow",
                               "prometheus", "aws"],
                "role": "Platform owner",
            },
            {
                "title": "Inference cost reduction",
                "description": "Profiled a recommendation service and cut serving cost by 41% "
                               "through batching, autoscaling and model right-sizing.",
                "tech_stack": ["python", "kubernetes", "aws", "observability"],
                "role": "Solo developer",
            },
        ],
        "education": [
            {
                "institution": "Example University of Science and Technology",
                "degree": "BSc",
                "field_of_study": "Computer Science",
                "start_year": 2016,
                "end_year": 2020,
            }
        ],
        "certifications": [
            {"name": "Certified Kubernetes Administrator", "issuer": "Example Cloud Institute",
             "issued_on": date(2023, 9, 1), "expires_on": date(2026, 9, 1)}
        ],
    },
    {
        "email": "sparse.student@careerlens.dev",
        "name": "Rafiul Islam",
        "headline": "Computer Science undergraduate",
        "career_goal": "Not sure yet - exploring what data work might suit me.",
        "bio": "Second-year student with a course project and a summer internship.",
        "location": "Rajshahi, Bangladesh",
        "education_level": "Undergraduate",
        "years_experience": 0,
        "preferred_role_family": "Data Science",
        "links": {},
        # Deliberately sparse: exercises the thin-profile path and the helpful
        # empty states rather than always showing a near-perfect match.
        "skills": {"python": 2, "sql": 2, "machine-learning": 1},
        "projects": [
            {
                "title": "Course project: movie recommendation",
                "description": "University group project using Python to build a simple "
                               "content-based recommender over a public movie dataset.",
                "tech_stack": ["python"],
                "role": "Team member",
            }
        ],
        "education": [
            {
                "institution": "Example University",
                "degree": "BSc",
                "field_of_study": "Computer Science",
                "start_year": 2023,
            }
        ],
        "certifications": [],
    },
]


def seed_user(db: Session, spec: dict) -> User:
    email = spec["email"].strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    created = user is None

    if created:
        user = User(
            name=spec["name"],
            email=email,
            password_hash=hash_password(DEMO_PASSWORD),
            role=UserRole.USER,
            is_active=True,
        )
        db.add(user)
        db.flush()

        db.add(
            Profile(
                user_id=user.id,
                headline=spec.get("headline"),
                career_goal=spec.get("career_goal"),
                bio=spec.get("bio"),
                location=spec.get("location"),
                education_level=spec.get("education_level"),
                years_experience=spec.get("years_experience"),
                preferred_role_family=spec.get("preferred_role_family"),
                links=spec.get("links", {}),
            )
        )
    else:
        user.name = spec["name"]
        user.password_hash = hash_password(DEMO_PASSWORD)
        user.is_active = True

    skills_by_slug = {skill.slug: skill for skill in db.scalars(select(Skill)).all()}
    for slug, proficiency in spec["skills"].items():
        skill = skills_by_slug.get(slug)
        if skill is None:
            logger.warning("Skipping unknown skill slug %r for %s", slug, email)
            continue
        existing = db.get(UserSkill, (user.id, skill.id))
        if existing is None:
            db.add(
                UserSkill(
                    user_id=user.id,
                    skill_id=skill.id,
                    proficiency=int(proficiency),
                    source=SkillSource.MANUAL.value,
                    confirmed=True,
                )
            )
        else:
            existing.proficiency = int(proficiency)

    db.flush()

    # Projects: replace wholesale so re-running converges rather than duplicating.
    db.query(Project).filter(Project.user_id == user.id).delete()
    for project in spec["projects"]:
        db.add(
            Project(
                user_id=user.id,
                title=project["title"],
                description=project["description"],
                tech_stack=project["tech_stack"],
                role=project.get("role"),
                is_public=True,
            )
        )

    db.query(EducationRecord).filter(EducationRecord.user_id == user.id).delete()
    for record in spec["education"]:
        db.add(EducationRecord(user_id=user.id, **record))

    db.query(Certification).filter(Certification.user_id == user.id).delete()
    for cert in spec["certifications"]:
        db.add(Certification(user_id=user.id, **cert))

    db.flush()
    return user


def main() -> int:
    with session_scope() as db:
        skills = len(db.scalars(select(Skill)).all())
        if skills == 0:
            raise SystemExit(
                "The skill taxonomy is empty. Run `python -m scripts.seed_taxonomy` first."
            )
        print(f"taxonomy skills available: {skills}")
        for spec in DEMO_USERS:
            seed_user(db, spec)
            print(f"  {spec['email']:32} skills={len(spec['skills']):2} "
                  f"projects={len(spec['projects'])} "
                  f"education={len(spec['education'])} certs={len(spec['certifications'])}")
    print(f"\nDemo password for every seeded user: {DEMO_PASSWORD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
