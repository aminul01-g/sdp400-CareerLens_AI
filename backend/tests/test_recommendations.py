"""T105/T106/T108 — recommendation generation, run history, and skill-gap analysis.

Also T150 (explainability as a correctness check) and T149 (latency).
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings


@pytest.fixture
def user_client(client: TestClient, make_user, taxonomy_seed, role_seed) -> TestClient:
    user = make_user(email="rec@example.com", name="Rec User")
    token = client.post(
        "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
    ).json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
def populated(user_client: TestClient, skill_ids: dict[str, int]) -> TestClient:
    user_client.post(
        "/api/profile",
        json={
            "headline": "Machine Learning Engineer",
            "career_goal": "Production MLOps work",
            "years_experience": 3,
        },
    )
    for slug, proficiency in (
        ("python", 5), ("sql", 4), ("scikit-learn", 4), ("pytorch", 4),
        ("docker", 3), ("aws", 3), ("pandas", 4),
    ):
        user_client.post("/api/skills", json={"skill_id": skill_ids[slug], "proficiency": proficiency})
    user_client.post(
        "/api/projects",
        json={
            "title": "Image classifier",
            "description": "Trained a CNN with PyTorch and served it with FastAPI on AWS.",
            "tech_stack": ["pytorch", "python", "docker", "aws"],
        },
    )
    user_client.post(
        "/api/education",
        json={"institution": "Example University", "degree": "BSc", "field_of_study": "Computer Science"},
    )
    return user_client


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------
def test_generate_requires_authentication(client: TestClient) -> None:
    assert client.post("/api/recommendations", json={}).status_code == 401


def test_empty_profile_returns_409_with_guidance(user_client: TestClient) -> None:
    """A list of sixty 0% roles is worse than one actionable error."""
    response = user_client.post("/api/recommendations", json={})
    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "profile_incomplete"
    assert "skill" in body["error"]["message"].lower()


def test_generate_returns_ranked_explainable_results(populated: TestClient) -> None:
    response = populated.post("/api/recommendations", json={"limit": 10})
    assert response.status_code == 201
    body = response.json()

    assert body["run_id"] > 0
    assert body["engine_version"]
    assert body["weights"] == {"skill_coverage": 0.6, "tfidf_similarity": 0.4}
    assert body["total_candidates"] >= len(body["results"])
    assert body["results"]

    for position, result in enumerate(body["results"], start=1):
        assert result["rank"] == position
        assert 0.0 <= result["compatibility_pct"] <= 100.0
        assert 0.0 <= result["skill_coverage"] <= 1.0
        assert 0.0 <= result["tfidf_similarity"] <= 1.0
        assert result["matched_skills"]
        assert isinstance(result["missing_skills"], list)
        for skill in result["matched_skills"]:
            assert skill["name"] and skill["weight"] > 0
            assert skill["proficiency"] is not None
        for skill in result["missing_skills"]:
            assert skill["name"] and skill["weight"] > 0
            assert skill["proficiency"] is None

    scores = [r["compatibility_pct"] for r in body["results"]]
    assert scores == sorted(scores, reverse=True)


def test_weights_and_contributions_are_shown(populated: TestClient) -> None:
    """The proposal requires the score to be explainable, not just present."""
    body = populated.post("/api/recommendations", json={"limit": 3}).json()
    for result in body["results"]:
        expected = round(0.6 * result["skill_coverage"] + 0.4 * result["tfidf_similarity"], 4)
        assert result["compatibility_pct"] == pytest.approx(
            round(expected * 100, 1), abs=0.2
        ), "the percentage is not the weighted combination of the two components"


def test_explainability_partitions_the_required_set(populated: TestClient) -> None:
    """T150: matched ∪ missing equals the role's required set, and is disjoint."""
    body = populated.post("/api/recommendations", json={"limit": 50}).json()
    for result in body["results"]:
        detail = populated.get(f"/api/jobs/{result['job_role_id']}").json()
        required = {s["skill_id"] for s in detail["skills"]}
        matched = {s["skill_id"] for s in result["matched_skills"]}
        missing = {s["skill_id"] for s in result["missing_skills"]}
        assert matched | missing == required, f"{result['title']}: union mismatch"
        assert not matched & missing, f"{result['title']}: overlap"
        assert len(matched) == result["matched_skills"].__len__()


def test_matched_and_missing_are_sorted_by_weight(populated: TestClient) -> None:
    for result in populated.post("/api/recommendations", json={"limit": 10}).json()["results"]:
        for group in ("matched_skills", "missing_skills"):
            weights = [s["weight"] for s in result[group]]
            assert weights == sorted(weights, reverse=True), f"{result['title']} {group}"


def test_limit_is_respected_and_validated(populated: TestClient) -> None:
    assert len(populated.post("/api/recommendations", json={"limit": 2}).json()["results"]) == 2
    assert populated.post("/api/recommendations", json={"limit": 0}).status_code == 422
    assert populated.post("/api/recommendations", json={"limit": 51}).status_code == 422


def test_role_family_filter(populated: TestClient) -> None:
    body = populated.post("/api/recommendations", json={"role_family": "ML Engineer"}).json()
    assert body["results"]
    assert {r["family"] for r in body["results"]} == {"ML Engineer"}


def test_min_score_filter(populated: TestClient) -> None:
    everything = populated.post("/api/recommendations", json={"limit": 50}).json()
    threshold = everything["results"][0]["compatibility_pct"] / 100
    filtered = populated.post(
        "/api/recommendations", json={"limit": 50, "min_score": threshold}
    ).json()
    assert all(r["compatibility_pct"] / 100 >= threshold for r in filtered["results"])


def test_generation_is_deterministic_for_one_user(populated: TestClient) -> None:
    first = populated.post("/api/recommendations", json={"limit": 20}).json()["results"]
    second = populated.post("/api/recommendations", json={"limit": 20}).json()["results"]
    assert [(r["job_role_id"], r["compatibility_pct"]) for r in first] == [
        (r["job_role_id"], r["compatibility_pct"]) for r in second
    ]


def test_generation_latency_is_under_two_seconds(populated: TestClient) -> None:
    """T149 / proposal section 7.5: 'within a few seconds'."""
    started = time.perf_counter()
    response = populated.post("/api/recommendations", json={"limit": 10})
    elapsed = time.perf_counter() - started
    assert response.status_code == 201
    assert elapsed < 2.0, f"took {elapsed:.2f}s for 25 skills against 4 seeded roles"


def test_generation_persists_a_run(populated: TestClient) -> None:
    """A run stores *every* candidate, not just the requested page.

    Truncating at storage time would make the stored record a partial one, and a
    partial history is not a history.
    """
    created = populated.post("/api/recommendations", json={"limit": 2}).json()
    run = populated.get(f"/api/recommendations/runs/{created['run_id']}").json()
    assert run["id"] == created["run_id"]
    assert run["weights"] == {"skill_coverage": 0.6, "tfidf_similarity": 0.4}
    assert run["profile_snapshot"]["skills"]
    assert len(run["results"]) == created["total_candidates"]
    assert [r["rank"] for r in run["results"]] == list(range(1, len(run["results"]) + 1))


def test_run_detail_matches_the_generation_response(populated: TestClient) -> None:
    created = populated.post("/api/recommendations", json={"limit": 5}).json()
    stored = populated.get(f"/api/recommendations/runs/{created['run_id']}").json()
    assert [r["job_role_id"] for r in stored["results"]][:5] == [
        r["job_role_id"] for r in created["results"]
    ]
    assert [r["rank"] for r in stored["results"]] == sorted(r["rank"] for r in stored["results"])


def test_run_history(populated: TestClient) -> None:
    populated.post("/api/recommendations", json={"limit": 3})
    populated.post("/api/recommendations", json={"limit": 3})
    history = populated.get("/api/recommendations/runs").json()
    assert history["total"] == 2
    assert history["items"][0]["id"] > history["items"][1]["id"], "newest first"
    assert history["items"][0]["top_role_title"]


def test_run_history_is_scoped_to_the_user(
    client: TestClient, populated: TestClient, make_user, taxonomy_seed
) -> None:
    populated.post("/api/recommendations", json={"limit": 3})
    other = make_user(email="other@example.com")
    other_client = TestClient(populated.app, raise_server_exceptions=False)
    token = other_client.post(
        "/api/auth/login", json={"email": other.email, "password": "Str0ngPassw0rd"}
    ).json()["access_token"]
    other_client.headers.update({"Authorization": f"Bearer {token}"})
    assert other_client.get("/api/recommendations/runs").json()["total"] == 0


# ---------------------------------------------------------------------------
# Skill gap
# ---------------------------------------------------------------------------
def test_skill_gap_requires_authentication(client: TestClient, role_seed) -> None:
    assert client.get(f"/api/skill-gap/{role_seed[0].id}").status_code == 401


def test_skill_gap_reports_matched_and_missing(populated: TestClient, role_seed) -> None:
    """The Data Scientist role is one this profile does not fully cover."""
    role_id = next(r.id for r in role_seed if r.family == "Data Analyst")
    body = populated.get(f"/api/skill-gap/{role_id}").json()

    assert body["job_role"]["title"]
    assert 0.0 <= body["coverage"] <= 1.0
    assert body["coverage_pct"] == round(body["coverage"] * 100, 1)
    assert body["matched_count"] > 0
    assert body["matched"] and body["missing"]

    for item in body["matched"]:
        assert item["proficiency"] >= 1
        assert item["weight"] > 0
        assert item["contribution"] > 0
    for item in body["missing"]:
        assert item["tier"] in {"critical", "important", "desirable"}


def test_fully_covered_role_reports_no_missing_skills(
    populated: TestClient, role_seed
) -> None:
    """Holding every required skill is **not** the same as full compatibility.

    This profile holds all six requirements of the seeded ML Engineer role, but
    Docker and AWS are at proficiency 3, which the ``(p-1)/4`` factor scores as
    0.5. So the gap list is empty while coverage is ~0.75. That distinction is
    the entire reason coverage is weighted by proficiency rather than by
    membership, and the UI must not present "you have every skill" as
    "100% compatible".
    """
    role_id = next(r.id for r in role_seed if r.family == "ML Engineer")
    body = populated.get(f"/api/skill-gap/{role_id}").json()
    assert body["missing"] == []
    assert body["missing_count"] == 0
    assert body["matched_count"] == body["required_count"] > 0
    assert body["coverage"] < 1.0, "membership alone must not read as full compatibility"
    assert any(m["proficiency"] < 5 for m in body["matched"])

    # Raising the weaker skills to 5 does reach full coverage.
    for matched in body["matched"]:
        if matched["proficiency"] < 5:
            assert populated.patch(
                f"/api/skills/{matched['skill_id']}", json={"proficiency": 5}
            ).status_code == 200
    assert populated.get(f"/api/skill-gap/{role_id}").json()["coverage"] == pytest.approx(
        1.0, abs=1e-6
    )


def test_skill_gap_orders_missing_by_descending_weight(populated: TestClient, role_seed) -> None:
    """The ordering is the feature: the first row is the most valuable thing to learn."""
    for role in role_seed:
        body = populated.get(f"/api/skill-gap/{role.id}").json()
        weights = [m["weight"] for m in body["missing"]]
        assert weights == sorted(weights, reverse=True), role.title


def test_skill_gap_tier_counts_match_the_items(populated: TestClient, role_seed) -> None:
    for role in role_seed:
        body = populated.get(f"/api/skill-gap/{role.id}").json()
        counts = {"critical": 0, "important": 0, "desirable": 0}
        for item in body["missing"]:
            counts[item["tier"]] += 1
        assert body["tiers"] == counts, role.title


def test_skill_gap_unknown_role_is_404(populated: TestClient) -> None:
    assert populated.get("/api/skill-gap/999999").status_code == 404


def test_skill_gap_for_a_user_with_no_skills(
    client: TestClient, make_user, role_seed
) -> None:
    """An empty profile must produce a full gap, not an error."""
    user = make_user(email="empty@example.com")
    http = TestClient(client.app, raise_server_exceptions=False)
    token = http.post(
        "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
    ).json()["access_token"]
    http.headers.update({"Authorization": f"Bearer {token}"})
    body = http.get(f"/api/skill-gap/{role_seed[0].id}").json()
    assert body["coverage"] == 0.0
    assert body["matched"] == []
    assert body["missing_count"] == body["required_count"]


def test_unconfirmed_cv_skills_do_not_appear_as_matched(
    client: TestClient, make_user, taxonomy_seed, role_seed
) -> None:
    """A staged extraction must neither count as matched nor suppress a gap."""
    import io

    import docx

    user = make_user(email="staged@example.com")
    http = TestClient(client.app, raise_server_exceptions=False)
    token = http.post(
        "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
    ).json()["access_token"]
    http.headers.update({"Authorization": f"Bearer {token}"})

    document = docx.Document()
    document.add_paragraph("SKILLS")
    for skill in ("Python", "SQL", "Scikit-learn", "PyTorch", "Docker", "TensorFlow", "Pandas"):
        document.add_paragraph(skill)
    buffer = io.BytesIO()
    document.save(buffer)

    upload = http.post(
        "/api/cv/upload",
        files={"file": ("cv.docx", buffer.getvalue(),
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    ).json()
    assert upload["detected_skills"], "the fixture should detect skills"

    ml_role = next(r.id for r in role_seed if r.family == "ML Engineer")
    gap = http.get(f"/api/skill-gap/{ml_role}").json()
    assert gap["matched"] == [], "unconfirmed skills appeared as matched"
    assert gap["coverage"] == 0.0

    # Confirm them, and now they do count.
    http.post(
        "/api/skills/confirm",
        json={"skills": [
            {"skill_id": s["skill_id"], "accepted": True, "proficiency": 4}
            for s in upload["detected_skills"]
        ]},
    )
    after = http.get(f"/api/skill-gap/{ml_role}").json()
    assert after["matched"]
    assert after["coverage"] > 0.0


# ---------------------------------------------------------------------------
# Optional LLM learning path
# ---------------------------------------------------------------------------
def test_learning_path_returns_503_when_disabled(populated: TestClient, role_seed) -> None:
    """A distinct, honest status proving the core path does not depend on the LLM."""
    assert get_settings().llm_enabled is False
    role_id = role_seed[0].id
    response = populated.post(f"/api/skill-gap/{role_id}/learning-path")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "feature_disabled"
    assert "without it" in response.json()["error"]["message"] or "complete without" in response.json()["error"]["message"]


def test_core_endpoints_ignore_the_learning_path_flag(
    populated: TestClient, role_seed
) -> None:
    """With the LLM off, everything else must work identically."""
    assert populated.get(f"/api/skill-gap/{role_seed[0].id}").status_code == 200
    assert populated.post("/api/recommendations", json={"limit": 3}).status_code == 201


def test_fallback_learning_path_is_deterministic_and_pure() -> None:
    from app.ml.learning_path import build_learning_path
    from app.ml.types import GapReport, MatchedSkill, MissingSkill, RoleSpec

    report = GapReport(
        job_role_id=1, title="ML Engineer", family="ML Engineer", coverage=0.5,
        matched=(MatchedSkill(1, "Python", 1.0, 5, 1.0),),
        missing=(
            MissingSkill(2, "Docker", 0.9, "critical"),
            MissingSkill(3, "Kubernetes", 0.6, "important"),
        ),
    )
    spec = RoleSpec(1, "ML Engineer", "ml", "ML Engineer", "d", {1: 1.0, 2: 0.9, 3: 0.6})

    steps, generated_by = build_learning_path(spec, report)  # no api key -> rules only
    assert generated_by == "careerlens-rules"
    assert [s["skill_name"] for s in steps] == ["Docker", "Kubernetes"]
    assert steps[0]["tier"] == "critical"
    assert steps[0]["guidance"]
    assert build_learning_path(spec, report)[0] == steps, "not deterministic"
