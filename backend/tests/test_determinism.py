"""T099 — the engine is deterministic, and the ML layer is isolated.

Determinism is what makes the Phase 9 evaluation reproducible, and the isolation
assertion is what keeps the engine replaceable: ``app/ml/*`` must never import an
ORM or a web framework, or it could not be unit-tested without a database, run as
``python -m app.ml.evaluation`` without an HTTP server, or be swapped without
touching a route.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.ml.ranker import rank
from app.ml.types import (
    CertificationFact,
    EducationFact,
    ProfileSnapshot,
    ProjectFact,
    RoleSpec,
    UserSkillFact,
)

ML_DIR = Path(__file__).resolve().parents[1] / "app" / "ml"
FORBIDDEN_MODULES = {"sqlalchemy", "fastapi", "starlette", "pydantic", "alembic", "psycopg"}
FORBIDDEN_SUBSTRINGS = ("sqlalchemy", "fastapi", "flask", "django")


@pytest.fixture
def snapshot() -> ProfileSnapshot:
    return ProfileSnapshot(
        user_id=1,
        headline="Machine Learning Engineer",
        career_goal="Production MLOps",
        bio="Builds models.",
        preferred_role_family="ML Engineer",
        skills=(
            UserSkillFact(1, 5, "Python", "python"),
            UserSkillFact(2, 4, "SQL", "sql"),
            UserSkillFact(3, 4, "Scikit-learn", "scikit-learn"),
            UserSkillFact(4, 3, "PyTorch", "pytorch"),
        ),
        projects=(
            ProjectFact("Classifier", "Built a CNN with PyTorch", ("python", "pytorch")),
            ProjectFact("Pipeline", "Streaming ETL with Spark", ("apache-spark", "sql")),
        ),
        education=(EducationFact("Example University", "BSc", "Computer Science"),),
        certifications=(CertificationFact("Deep Learning Specialization", "Example"),),
    )


@pytest.fixture
def roles() -> list[RoleSpec]:
    return [
        RoleSpec(i, f"Role {i}", f"role-{i}", "Family",
                 f"Description for role {i} involving machine learning and data pipelines.",
                 {1: 1.0, 2: 0.8, 3: 0.6, 4: 0.4})
        for i in range(1, 21)
    ]


def _serialise(scores) -> list[tuple]:
    return [
        (
            s.job_role_id,
            s.rank,
            round(s.compatibility, 12),
            round(s.skill_coverage, 12),
            round(s.tfidf_similarity, 12),
            tuple((m.skill_id, m.proficiency) for m in s.matched),
            tuple((x.skill_id, x.tier) for x in s.missing),
        )
        for s in scores
    ]


def test_two_ranker_runs_are_identical(snapshot: ProfileSnapshot, roles) -> None:
    first = _serialise(rank(snapshot, roles))
    second = _serialise(rank(snapshot, roles))
    assert first == second


def test_repeated_runs_remain_identical(snapshot: ProfileSnapshot, roles) -> None:
    baseline = _serialise(rank(snapshot, roles))
    for _ in range(5):
        assert _serialise(rank(snapshot, roles)) == baseline


def test_input_order_of_roles_does_not_change_the_ranking(
    snapshot: ProfileSnapshot, roles
) -> None:
    forward = _serialise(rank(snapshot, roles))
    backward = _serialise(rank(snapshot, list(reversed(roles))))
    assert [row[0] for row in forward] == [row[0] for row in backward]
    assert forward == backward


def test_identical_twin_roles_are_ordered_by_id(snapshot: ProfileSnapshot) -> None:
    twins = [
        RoleSpec(90, "Twin A", "twin-a", "F", "Same description.", {1: 1.0}),
        RoleSpec(10, "Twin B", "twin-b", "F", "Same description.", {1: 1.0}),
    ]
    assert [s.job_role_id for s in rank(snapshot, twins)] == [10, 90]


def test_profile_text_is_deterministic(snapshot: ProfileSnapshot) -> None:
    from app.ml.text_profile import build_profile_text

    assert build_profile_text(snapshot) == build_profile_text(snapshot)


def test_profile_text_weights_skills_by_proficiency() -> None:
    from app.ml.text_profile import build_profile_text

    weighted = build_profile_text(ProfileSnapshot(
        user_id=1, skills=(UserSkillFact(1, 5, "TensorFlow", "tensorflow"),)
    ))
    assert weighted.split().count("TensorFlow") == 5

    light = build_profile_text(ProfileSnapshot(
        user_id=1, skills=(UserSkillFact(1, 1, "TensorFlow", "tensorflow"),)
    ))
    assert light.split().count("TensorFlow") == 1


def test_profile_text_includes_projects_and_education(snapshot: ProfileSnapshot) -> None:
    from app.ml.text_profile import build_profile_text

    text = build_profile_text(snapshot)
    for expected in ("Classifier", "Pipeline", "BSc", "Computer Science",
                     "Example University", "Deep Learning Specialization",
                     "Machine Learning Engineer", "Production MLOps"):
        assert expected in text, f"{expected!r} missing from the profile text"


# ---------------------------------------------------------------------------
# ML isolation
# ---------------------------------------------------------------------------
def _python_files() -> list[Path]:
    return sorted(ML_DIR.rglob("*.py"))


def test_ml_directory_exists_and_has_the_planned_modules() -> None:
    names = {p.name for p in _python_files()}
    for expected in (
        "types.py", "taxonomy.py", "text_loader.py", "extractor.py",
        "text_profile.py", "matcher.py", "gap_analysis.py", "ranker.py",
    ):
        assert expected in names, f"app/ml/{expected} is missing"
    assert "learning_path.py" in names, "the optional learning path module is absent"


def _code_lines_only(path: Path) -> list[tuple[int, str]]:
    """Source lines with comments and string literals removed.

    The isolation rule is about *code*, not prose. ``types.py`` documents that it
    must not import SQLAlchemy, and a naive grep would flag the docstring that says
    so — which is exactly how a check like this silently stops being checked.
    """
    import io
    import tokenize

    source = path.read_text(encoding="utf-8")
    out: list[tuple[int, str]] = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type in (tokenize.COMMENT, tokenize.STRING):
            continue
        out.append((token.start[0], token.line.rstrip()))
    return out


def test_ml_imports_no_orm_or_framework() -> None:
    """The plan's grep gate: ``grep -rn "sqlalchemy\\|fastapi" backend/app/ml/``.

    Comments and string literals are excluded so that the docstrings *documenting*
    the rule do not trip it. ``test_ml_imports_no_forbidden_top_level_modules``
    below is the authoritative, AST-based check.
    """
    offenders: list[str] = []
    for path in _python_files():
        for lineno, line in _code_lines_only(path):
            lowered = line.lower()
            for needle in FORBIDDEN_SUBSTRINGS:
                if needle in lowered:
                    offenders.append(f"{path.relative_to(ML_DIR)}:{lineno}: {line.strip()}")
    assert not offenders, "app/ml code must not reference the ORM or a web framework:\n" + "\n".join(
        offenders
    )


def test_the_isolation_rule_is_actually_documented_in_the_code() -> None:
    """Guard the guard: the docstrings stating the rule must keep existing."""
    types_doc = (ML_DIR / "types.py").read_text(encoding="utf-8")
    assert "must not import" in types_doc.lower()


def test_ml_imports_no_forbidden_top_level_modules() -> None:
    """AST-level check, so an aliased or indirect import cannot slip through."""
    offenders: list[str] = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module.split(".")[0]]
            for name in names:
                if name in FORBIDDEN_MODULES:
                    offenders.append(f"{path.relative_to(ML_DIR)}: imports {name}")
    assert not offenders, f"forbidden imports in app/ml: {offenders}"


def test_ml_only_imports_from_app_ml_and_allowed_third_party() -> None:
    """The ML layer may import the standard library, its own package, and ML libs."""
    allowed_third_party = {
        "spacy", "sklearn", "numpy", "pandas", "scipy", "scikit_learn",
        # The CV parsers. They are format libraries, not frameworks, and
        # text_loader.py is their only consumer.
        "pdfplumber", "docx",
        "json", "re", "math", "os", "sys", "pathlib", "logging", "typing",
        "dataclasses", "functools", "collections", "decimal", "datetime",
        "enum", "urllib", "hashlib", "itertools", "random", "statistics",
        "__future__", "time", "copy", "abc",
    }
    offenders: list[str] = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            module: str | None = None
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    if top not in allowed_third_party and not alias.name.startswith("app."):
                        offenders.append(f"{path.relative_to(ML_DIR)}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.level:  # relative, i.e. inside app.ml
                    continue
                module = node.module or ""
                top = module.split(".")[0]
                if module.startswith("app."):
                    if not module.startswith("app.ml"):
                        offenders.append(f"{path.relative_to(ML_DIR)}: from {module}")
                elif top not in allowed_third_party:
                    offenders.append(f"{path.relative_to(ML_DIR)}: from {module}")
    assert not offenders, f"app/ml must not reach outside itself: {offenders}"


def test_ml_layer_runs_without_a_database() -> None:
    """Importing and running the engine must not require a live database."""
    import subprocess
    import sys

    code = (
        "import sys;"
        "from app.ml.ranker import rank;"
        "from app.ml.types import ProfileSnapshot, UserSkillFact, RoleSpec;"
        "s=ProfileSnapshot(user_id=1, skills=(UserSkillFact(1,5,'Python','python'),));"
        "r=[RoleSpec(1,'R','r','F','Machine learning with Python.',{1:1.0})];"
        "out=rank(s,r);"
        "assert out[0].compatibility>0;"
        "assert 'sqlalchemy' not in sys.modules, 'the ORM was imported';"
        "print('OK', round(out[0].compatibility,4))"
    )
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=root, capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_no_randomness_in_the_ml_layer() -> None:
    """A random source would make the evaluation irreproducible."""
    offenders = [
        f"{path.relative_to(ML_DIR)}:{lineno}"
        for path in _python_files()
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if "random." in line and not line.strip().startswith("#")
    ]
    assert not offenders, f"randomness found in app/ml: {offenders}"


def test_no_create_all_in_the_application() -> None:
    """Alembic owns the schema. ``create_all`` belongs only in test scaffolding."""
    app_dir = ML_DIR.parents[0]
    offenders = [
        str(path.relative_to(app_dir))
        for path in app_dir.rglob("*.py")
        if "create_all" in path.read_text(encoding="utf-8")
    ]
    assert not offenders, f"create_all found in application code: {offenders}"
