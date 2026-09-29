"""Test fixtures.

Two decisions here matter for the whole suite:

1. **A separate database.** ``careerlens_test``. Tests must never touch
   development data, and a test that migrates and drops tables would be
   catastrophic against the dev database.
2. **The schema is created by Alembic, not ``create_all()``.** The plan permits
   ``Base.metadata.create_all()`` only in this file, and using it *here* would
   still be a mistake: the tests would then pass against a schema Alembic never
   produced, and a broken migration would go unnoticed until production. Running
   real migrations is the only way to test the migration itself.

Each test runs in a transaction that is rolled back afterwards, so tests are
independent and leave no residue.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Generator, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Set before app modules are imported so Settings picks up the test database.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-that-is-definitely-long-enough-123456")

import logging

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import *  # noqa: F403  (register every mapper)
from app.models.user import User, UserRole

logger = logging.getLogger("tests.conftest")

TEST_DATABASE_URL = get_settings().test_database_url


def _admin_url() -> URL:
    """Connect to the maintenance database to CREATE DATABASE if needed.

    Returns the ``URL`` object rather than ``str(url)``: SQLAlchemy 2.0 renders a
    URL's password as ``***`` when stringified, so round-tripping through ``str``
    silently authenticates with the literal three asterisks.
    """
    return make_url(TEST_DATABASE_URL).set(database="postgres")


@pytest.fixture(scope="session")
def test_database() -> Generator[str, None, None]:
    """Create the test database once per session, then build the schema via Alembic."""
    from alembic import command
    from alembic.config import Config

    # 1. Ensure the database exists.
    maintenance = create_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    with maintenance.connect() as connection:
        db_name = make_url(TEST_DATABASE_URL).database
        assert db_name, "test_database_url must name a database"
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": db_name}
        ).scalar()
        if not exists:
            # Identifier cannot be bound as a parameter, so it is quoted instead.
            connection.execute(text(f'CREATE DATABASE "{db_name}"'))
            logger.info("Created test database %s", db_name)
    maintenance.dispose()

    # 2. Migrate it with the real Alembic chain.
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    get_settings.cache_clear()
    alembic_cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    command.upgrade(alembic_cfg, "head")

    # 3. Verify the core schema is actually there.
    engine = create_engine(TEST_DATABASE_URL)
    with engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
                )
            ).all()
        }
    engine.dispose()
    required = {
        "user", "profile", "skill", "skill_alias", "user_skill", "project",
        "education_record", "certification", "job_role", "job_role_skill",
        "resume_upload", "resume_detected_skill", "recommendation_run",
        "recommendation_result",
    }
    missing = required - tables
    assert not missing, f"Migrations did not create: {sorted(missing)}"

    yield TEST_DATABASE_URL


@pytest.fixture(scope="session")
def engine(test_database: str) -> Generator[Engine, None, None]:
    session_engine = create_engine(
        test_database, pool_pre_ping=True, future=True
    )
    yield session_engine
    session_engine.dispose()


@pytest.fixture
def _isolated_session(engine: Engine) -> Generator[Session, None, None]:
    """One connection, one transaction, one session — per test.

    **Both** ``db`` and ``client`` must come from here. When they open separate
    connections, a test that writes through the API while also asserting via
    ``db`` will block on the first connection's row lock and the suite deadlocks.
    Sharing a single session also means the test can see exactly what the API
    wrote, and the rollback at teardown leaves nothing behind.
    """
    connection = engine.connect()
    transaction = connection.begin()
    # join_transaction_mode="create_savepoint" is essential. Without it, a
    # `session.commit()` inside a service *commits the outer transaction too*, so
    # rows written by a test survive into the next one and eventually collide on
    # unique constraints. With savepoints, an inner commit only releases a
    # savepoint, and the outer rollback at teardown genuinely discards everything.
    session = sessionmaker(
        bind=connection,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def db(_isolated_session: Session) -> Session:
    """Direct database access for a test."""
    return _isolated_session


@pytest.fixture
def client(_isolated_session: Session) -> Iterator[TestClient]:
    """A TestClient whose ``get_db`` yields the same session ``db`` exposes."""
    from app.db.session import get_db
    from app.main import create_app

    application = create_app()
    application.dependency_overrides[get_db] = lambda: _isolated_session

    with TestClient(application, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def raw_client() -> Iterator[TestClient]:
    """A TestClient with **no** database override, for testing the real ``get_db``.

    Used by ``test_ml_isolation`` and any check that must exercise the production
    dependency rather than the overridden one.
    """
    from app.main import create_app

    with TestClient(create_app(), raise_server_exceptions=False) as test_client:
        yield test_client


# No autouse teardown is needed: `client` is function-scoped and builds a fresh
# application per test, so dependency overrides cannot leak between tests.
# (An autouse fixture that called getfixturevalue("client") to clear overrides
# actually *forced* the client to be created — and then torn down — for tests
# that never asked for it, which surfaced as "fixture value is not available".)


# ---------------------------------------------------------------------------
# Domain fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def make_user(db: Session):
    """Factory for users. ``role='admin'`` is all a test needs to change."""

    def _make(
        *,
        email: str | None = None,
        name: str = "Test User",
        password: str = "Str0ngPassw0rd",
        role: UserRole = UserRole.USER,
        is_active: bool = True,
    ) -> User:
        from app.models.profile import Profile

        user = User(
            name=name,
            email=email or f"user{db.query(User).count()}-{id(db) % 100000}@example.com",
            password_hash=hash_password(password),
            role=role,
            is_active=is_active,
        )
        db.add(user)
        db.flush()
        db.add(Profile(user_id=user.id))
        db.flush()
        return user

    return _make


@pytest.fixture
def sample_user(make_user) -> User:
    return make_user(email="user@example.com", name="Sample User")


@pytest.fixture
def sample_admin(make_user) -> User:
    return make_user(email="admin@example.com", name="Sample Admin", role=UserRole.ADMIN)


@pytest.fixture
def auth_client(client: TestClient, make_user):
    """A client already carrying a Bearer token for a fresh user."""

    def _login(role: str = "user", **kwargs) -> tuple[TestClient, User]:
        from app.models.user import UserRole

        user = make_user(role=UserRole(role), **kwargs)
        response = client.post(
            "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
        )
        assert response.status_code == 200, response.text
        client.headers.update({"Authorization": f"Bearer {response.json()['access_token']}"})
        return client, user

    return _login


@pytest.fixture
def taxonomy_seed(db: Session) -> list:
    """A small, hand-picked slice of the taxonomy. Enough for ML and CRUD tests."""
    from app.models.skill import Skill, SkillAlias

    data = [
        ("Python", "python", "Programming & Core", ["py3", "python3"]),
        ("SQL", "sql", "Data Engineering", ["structured query language"]),
        ("Scikit-learn", "scikit-learn", "ML Frameworks", ["sklearn", "scikit learn", "sk-learn"]),
        ("PyTorch", "pytorch", "Deep Learning", ["torch", "py-torch"]),
        ("Docker", "docker", "MLOps & Cloud", ["dockerfile", "containers"]),
        ("AWS", "aws", "MLOps & Cloud", ["amazon web services"]),
        ("FastAPI", "fastapi", "Analytics & Communication", ["fastapi api"]),
        ("Pandas", "pandas", "Data Engineering", ["pd"]),
        ("JavaScript", "javascript", "Programming & Core", ["js", "node.js"]),
        ("Java", "java", "Programming & Core", ["java8"]),
        ("MongoDB", "mongodb", "Data Engineering", ["mongo"]),
        ("Go", "golang", "Programming & Core", ["golang", "go language"]),
        ("TensorFlow", "tensorflow", "ML Frameworks", ["tf"]),
        ("spaCy", "spacy", "NLP & LLM", ["spacy nlp"]),
        ("PostgreSQL", "postgresql", "Data Engineering", ["postgres", "psql"]),
        ("Apache Spark", "apache-spark", "Data Engineering", ["spark", "pyspark"]),
        ("Machine Learning", "machine-learning", "ML Frameworks", ["ml"]),
        ("Deep Learning", "deep-learning", "Deep Learning", ["dl"]),
    ]
    skills = []
    for name, slug, category, aliases in data:
        skill = Skill(name=name, slug=slug, category=category, description=f"{name} seed entry")
        db.add(skill)
        db.flush()
        db.add_all([SkillAlias(alias=a, skill_id=skill.id) for a in aliases])
        skills.append(skill)
    db.flush()
    return skills


@pytest.fixture
def role_seed(db: Session, taxonomy_seed) -> list:
    """A handful of job roles with weighted required skills."""
    from decimal import Decimal

    from app.models.job import JobRole, JobRoleSkill
    from app.schemas.job import slugify

    by_slug = {s.slug: s for s in taxonomy_seed}
    data = [
        (
            "Machine Learning Engineer",
            "ML Engineer",
            "Mid",
            "Design, train, and deploy machine learning models using Python, Scikit-learn and PyTorch. "
            "Work with SQL for feature pipelines and Docker for reproducible serving.",
            {"python": 1.0, "scikit-learn": 0.9, "pytorch": 0.85, "sql": 0.7, "docker": 0.6, "aws": 0.4},
        ),
        (
            "AI Engineer",
            "AI Engineer",
            "Mid",
            "Build end-to-end AI products: Python services, FastAPIs, model serving with Docker, "
            "and machine learning pipelines deployed on AWS.",
            {"python": 1.0, "sql": 0.8, "scikit-learn": 0.85, "pytorch": 0.7, "docker": 0.75, "fastapi": 0.6, "aws": 0.6},
        ),
        (
            "Data Analyst",
            "Data Analyst",
            "Junior",
            "Answer business questions with SQL and Python, building clear dashboards from tabular data.",
            {"sql": 1.0, "python": 0.8, "pandas": 0.75, "postgresql": 0.4},
        ),
        (
            "Frontend Engineer",
            "Frontend Engineer",
            "Mid",
            "Build responsive web applications with JavaScript and modern frameworks.",
            {"javascript": 1.0, "python": 0.2},
        ),
    ]
    roles = []
    for title, family, seniority, description, skills in data:
        role = JobRole(
            title=title,
            slug=slugify(title),
            family=family,
            seniority=seniority,
            description=description,
            responsibilities=[],
            is_active=True,
        )
        db.add(role)
        db.flush()
        for slug, weight in skills.items():
            if slug in by_slug:
                db.add(
                    JobRoleSkill(
                        job_role_id=role.id, skill_id=by_slug[slug].id, weight=Decimal(str(weight))
                    )
                )
        roles.append(role)
    db.flush()
    return roles


@pytest.fixture
def skill_ids(taxonomy_seed) -> dict[str, int]:
    return {skill.slug: skill.id for skill in taxonomy_seed}
