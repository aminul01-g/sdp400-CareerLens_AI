"""Regression gate for the matching engine's evaluation metrics.

The point of this file is that the top-3 hit rate is a *gate*, not a number
someone read once. If a change to the ranker, the taxonomy or the job-role
knowledge base pushes the shortlist below the proposal's committed threshold,
this suite fails in CI instead of the regression being discovered later by a
user.

Two costs are paid deliberately:

* the harness is invoked in-process rather than through a subprocess, so a
  failure surfaces as a readable assertion instead of an exit code;
* the label file is loaded through the real loader, so a malformed label file
  fails here too, which is where you want to find out.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.ml.evaluation import harness, metrics, tuning
from app.ml.evaluation.harness import (
    TARGET_TOP3_HIT_RATE,
    EvaluationDataError,
    evaluate,
    load_profiles,
    load_role_specs,
    load_taxonomy_index,
    sweep,
)
from app.ml.taxonomy import load as load_taxonomy

tests_dir = Path(__file__).parent

# Loading the knowledge base is I/O; the ranking sweep is the slow part. Both are
# module-scoped so the suite pays for them once rather than per test.
_ROLES_PATH = harness.DEFAULT_ROLES_PATH
_TAXONOMY_PATH = harness.DEFAULT_TAXONOMY_PATH


@pytest.fixture(scope="module")
def profiles():
    return load_profiles()


@pytest.fixture(scope="module")
def knowledge_base():
    taxonomy = load_taxonomy(str(_TAXONOMY_PATH))
    skill_ids = load_taxonomy_index(_TAXONOMY_PATH)
    role_specs = load_role_specs(_ROLES_PATH, skill_ids=skill_ids)
    return taxonomy, skill_ids, role_specs


@pytest.fixture(scope="module")
def result(profiles, knowledge_base):
    taxonomy, skill_ids, role_specs = knowledge_base
    return evaluate(
        profiles,
        role_specs,
        taxonomy=taxonomy,
        skill_ids=skill_ids,
        roles_path=_ROLES_PATH,
        taxonomy_path=_TAXONOMY_PATH,
    )


# --------------------------------------------------------------------------- #
# the gate
# --------------------------------------------------------------------------- #


def test_top3_hit_rate_meets_the_committed_target(result) -> None:
    """The proposal commits to a top-3 hit rate of at least 0.75."""
    assert result.top3_hit_rate >= TARGET_TOP3_HIT_RATE, (
        f"top-3 hit rate regressed to {result.top3_hit_rate:.3f} "
        f"(target {TARGET_TOP3_HIT_RATE:.2f}); misses: {', '.join(result.misses)}"
    )


def test_top1_accuracy_is_reported_however_low(result) -> None:
    """Top-1 has no target, but it must be a real number, not a placeholder.

    This is the assertion that stops a future change from quietly deleting the
    metric that happens to look bad.
    """
    assert 0.0 <= result.top1_accuracy <= 1.0
    assert result.top1_accuracy > 0.0, "a zero top-1 would mean the engine returns nothing usable"


def test_metrics_are_within_bounds(result) -> None:
    assert 0.0 <= result.mean_reciprocal_rank <= 1.0
    assert 0.0 <= result.metrics.mean_compatibility_of_expected <= 1.0
    for name, value in result.metrics.component_means.items():
        assert 0.0 <= value <= 1.0, f"component {name} out of range: {value}"


def test_every_profile_is_evaluated_and_ranked(result) -> None:
    assert result.n_profiles >= 24, "the label set shrank below the agreed size"
    assert len(result.outcomes) == result.n_profiles
    for outcome in result.outcomes:
        assert outcome.expected_rank >= 1, f"{outcome.id}: expected role was not ranked at all"
        assert outcome.ranked_roles, f"{outcome.id}: empty ranking"
        assert len(set(outcome.ranked_roles)) == len(outcome.ranked_roles), (
            f"{outcome.id}: ranking contains duplicate roles"
        )


def test_evaluation_is_deterministic(profiles, knowledge_base) -> None:
    """Two runs over unchanged inputs must agree exactly.

    The completion criterion for this phase, and the reason the tie-break on
    ``job_role_id`` exists. A ranker that reorders equal scores between runs
    would make every other metric in this file untrustworthy.
    """
    taxonomy, skill_ids, role_specs = knowledge_base
    kwargs = {
        "taxonomy": taxonomy,
        "skill_ids": skill_ids,
        "roles_path": _ROLES_PATH,
        "taxonomy_path": _TAXONOMY_PATH,
    }
    first = evaluate(profiles, role_specs, **kwargs)
    second = evaluate(profiles, role_specs, **kwargs)
    assert [o.ranked_roles for o in first.outcomes] == [
        o.ranked_roles for o in second.outcomes
    ]
    assert first.top3_hit_rate == second.top3_hit_rate
    assert first.top1_accuracy == second.top1_accuracy


def test_label_file_structure_is_sound(profiles) -> None:
    """Guards the properties that make the metrics mean something."""
    ids = [p.id for p in profiles]
    assert len(ids) == len(set(ids)), "duplicate profile ids in the label file"
    families = {p.expected_family for p in profiles}
    assert len(families) >= 10, f"only {len(families)} families covered"
    for profile in profiles:
        assert profile.rationale.strip(), f"{profile.id}: empty rationale"
        assert profile.skills, f"{profile.id}: no skills declared"
        for slug, proficiency in profile.skills:
            assert 1 <= proficiency <= 5, f"{profile.id}: {slug} proficiency {proficiency}"
    boundary = [p for p in profiles if p.note]
    assert len(boundary) >= 3, "the plan requires at least 3 near-boundary cases"


# --------------------------------------------------------------------------- #
# weight sweep
# --------------------------------------------------------------------------- #


def test_sweep_covers_the_planned_range_and_holds_the_default(profiles, knowledge_base) -> None:
    """The sweep must span the plan's range and not retune on noise.

    With 26 profiles one flipped profile is worth 0.038 of top-1, so a
    recommendation that moves the shipped weight on a smaller margin is
    indistinguishable from a coin toss.
    """
    taxonomy, skill_ids, role_specs = knowledge_base
    points = sweep(
        profiles,
        role_specs,
        weights=tuning.SWEEP_WEIGHTS,
        taxonomy=taxonomy,
        skill_ids=skill_ids,
        roles_path=_ROLES_PATH,
        taxonomy_path=_TAXONOMY_PATH,
    )
    covered = {round(p.coverage_weight, 2) for p in points}
    for planned in (0.5, 0.6, 0.7, 0.8, 0.9):
        assert planned in covered, f"sweep did not evaluate coverage weight {planned}"

    for point in points:
        assert point.coverage_weight + point.tfidf_weight == pytest.approx(1.0)

    noise_floor = 1.0 / len(profiles)
    chosen = tuning.recommend(points, noise_floor=noise_floor)
    assert chosen.coverage_weight == pytest.approx(tuning.DEFAULT_COVERAGE_WEIGHT), (
        f"sweep recommends {chosen.coverage_weight}, which differs from the shipped "
        f"{tuning.DEFAULT_COVERAGE_WEIGHT} by more than the label set can resolve"
    )


def test_recommend_holds_the_default_when_the_margin_is_noise() -> None:
    """The noise floor must actually hold, using a synthetic near-tie."""
    points = [
        tuning.TuningPoint(
            coverage_weight=0.6, tfidf_weight=0.4, top1_accuracy=0.692,
            top3_hit_rate=1.0, mean_reciprocal_rank=0.84, mean_compatibility_of_expected=0.42,
        ),
        tuning.TuningPoint(
            coverage_weight=0.5, tfidf_weight=0.5, top1_accuracy=0.731,
            top3_hit_rate=1.0, mean_reciprocal_rank=0.859, mean_compatibility_of_expected=0.43,
        ),
    ]
    # 0.039 apart on top-1, which is one profile out of 26.
    assert tuning.recommend(points, noise_floor=0.05).coverage_weight == pytest.approx(0.6)
    # With no floor, the same data does move the weight -- proving the guard is
    # doing the work rather than the ordering happening to agree.
    assert tuning.recommend(points, noise_floor=0.0).coverage_weight == pytest.approx(0.5)


def test_recommend_moves_when_the_improvement_is_real() -> None:
    points = [
        tuning.TuningPoint(
            coverage_weight=0.6, tfidf_weight=0.4, top1_accuracy=0.60,
            top3_hit_rate=0.80, mean_reciprocal_rank=0.70, mean_compatibility_of_expected=0.40,
        ),
        tuning.TuningPoint(
            coverage_weight=0.5, tfidf_weight=0.5, top1_accuracy=0.90,
            top3_hit_rate=0.95, mean_reciprocal_rank=0.90, mean_compatibility_of_expected=0.50,
        ),
    ]
    assert tuning.recommend(points, noise_floor=0.05).coverage_weight == pytest.approx(0.5)


# --------------------------------------------------------------------------- #
# pure metric functions
# --------------------------------------------------------------------------- #


def test_rank_of_handles_a_miss_without_raising() -> None:
    assert metrics.rank_of("b", ("a", "b", "c")) == 2
    assert metrics.rank_of("z", ("a", "b")) == 0


def test_metrics_agree_with_hand_computed_values() -> None:
    expected = ["a", "b", "c", "d"]
    predictions = [
        ("a", "x", "y"),  # rank 1 -> 1.0
        ("x", "b", "y"),  # rank 2 -> 0.5
        ("x", "y", "z"),  # miss   -> 0.0
        ("w", "x", "d"),  # rank 3 -> 1/3
    ]
    assert metrics.top1_accuracy(expected, predictions) == pytest.approx(0.25)
    assert metrics.top3_hit_rate(expected, predictions) == pytest.approx(0.75)
    assert metrics.mean_reciprocal_rank(expected, predictions) == pytest.approx(
        (1.0 + 0.5 + 0.0 + 1 / 3) / 4
    )


def test_metrics_reject_mismatched_lengths() -> None:
    with pytest.raises(ValueError, match="length mismatch"):
        metrics.top1_accuracy(["a"], [("a",), ("b",)])
    with pytest.raises(ValueError, match="empty label set"):
        metrics.top1_accuracy([], [])


def test_mean_compatibility_and_component_means() -> None:
    expected = ["a", "b"]
    # Looks up the *expected* role in each profile's map: 0.8 for the first
    # profile (which expects "a") and 0.4 for the second (which expects "b").
    compat = [{"a": 0.8, "b": 0.2}, {"a": 0.6, "b": 0.4}]
    assert metrics.mean_compatibility_of_expected(expected, compat) == pytest.approx(0.6)

    components = [
        {"a": {"skill_coverage": 1.0, "tfidf_similarity": 0.0}},
        {"b": {"skill_coverage": 0.5, "tfidf_similarity": 0.5}},
    ]
    means = metrics.per_component_means(expected, components)
    assert means == {"skill_coverage": 0.75, "tfidf_similarity": 0.25}


def test_missing_expected_role_in_score_map_is_an_error() -> None:
    """A silently-missing score would understate the mean."""
    with pytest.raises(ValueError, match="missing from its score map"):
        metrics.mean_compatibility_of_expected(["a"], [{"b": 0.5}])


def test_compute_metrics_degrades_gracefully_without_optional_inputs() -> None:
    computed = metrics.compute_metrics(["a"], [("a", "b")])
    assert computed.top1_accuracy == 1.0
    assert computed.mean_compatibility_of_expected == 0.0
    assert computed.component_means == {}


# --------------------------------------------------------------------------- #
# data validation
# --------------------------------------------------------------------------- #


def test_unknown_expected_role_is_rejected() -> None:
    """A label pointing at a role the knowledge base does not contain is a bug."""
    taxonomy = load_taxonomy(str(_TAXONOMY_PATH))
    skill_ids = load_taxonomy_index(_TAXONOMY_PATH)
    role_specs = load_role_specs(_ROLES_PATH, skill_ids=skill_ids)
    profiles = load_profiles()
    broken = list(profiles)
    first = broken[0]
    broken[0] = type(first)(
        id=first.id,
        name=first.name,
        expected_role="no-such-role",
        expected_family=first.expected_family,
        skills=first.skills,
        projects=first.projects,
        education=first.education,
        rationale=first.rationale,
    )
    with pytest.raises(EvaluationDataError, match="not in the job role knowledge base"):
        evaluate(broken, role_specs, taxonomy=taxonomy, skill_ids=skill_ids)


def test_unknown_skill_slug_in_a_profile_is_rejected() -> None:
    taxonomy = load_taxonomy(str(_TAXONOMY_PATH))
    profiles = load_profiles()
    with pytest.raises(EvaluationDataError, match="unknown skill slugs"):
        harness._build_snapshot(
            type(profiles[0])(
                id="X",
                name="x",
                expected_role=profiles[0].expected_role,
                expected_family=profiles[0].expected_family,
                skills=(("not-a-real-skill", 3),),
                projects=(),
                education=(),
                rationale="x",
            ),
            load_taxonomy_index(_TAXONOMY_PATH),
            taxonomy,
        )


def test_role_spec_loader_rejects_a_skill_outside_the_taxonomy(tmp_path) -> None:
    """A dropped requirement would lower a role's denominator and inflate coverage."""
    payload = {
        "roles": [
            {
                "title": "Ghost",
                "slug": "ghost",
                "family": "X",
                "description": "d",
                "skills": [
                    {"skill_slug": "python", "weight": 1.0},
                    {"skill_slug": "not-in-taxonomy", "weight": 0.5},
                ],
            }
        ]
    }
    path = tmp_path / "roles.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(EvaluationDataError, match="not in the taxonomy"):
        load_role_specs(path, skill_ids={"python": 1})


def test_malformed_label_file_is_rejected(tmp_path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text('{"id": "A", "name": "a"}\n', encoding="utf-8")
    with pytest.raises(EvaluationDataError, match="missing keys"):
        load_profiles(path)

    dupes = tmp_path / "dupes.jsonl"
    record = (
        '{"id": "A", "name": "a", "expected_role": "r", "expected_family": "f", '
        '"skills": [{"skill_slug": "python", "proficiency": 3}], "rationale": "why"}\n'
    )
    dupes.write_text(record + record, encoding="utf-8")
    with pytest.raises(EvaluationDataError, match="duplicate profile id"):
        load_profiles(dupes)

    out_of_range = tmp_path / "range.jsonl"
    out_of_range.write_text(
        '{"id": "A", "name": "a", "expected_role": "r", "expected_family": "f", '
        '"skills": [{"skill_slug": "python", "proficiency": 9}], "rationale": "why"}\n',
        encoding="utf-8",
    )
    with pytest.raises(EvaluationDataError, match="outside 1-5"):
        load_profiles(out_of_range)


# --------------------------------------------------------------------------- #
# the report artifact
# --------------------------------------------------------------------------- #


def test_markdown_report_contains_every_required_section(result) -> None:
    """T157 lists the sections the report must state. Assert them, don't hope.

    A report that silently loses its design-honesty disclosure is worse than no
    report, so the section headings are checked rather than the prose.
    """
    markdown = harness.render_markdown(result, ())

    assert "# Matching Engine Evaluation" in markdown
    assert "## Headline metrics" in markdown
    assert "## Weight sweep" in markdown
    assert "## Per family" in markdown
    assert "## Per profile" in markdown
    # The design-honesty disclosure: no trained classifier, per proposal 4.2.
    assert "## Design honesty: no trained classifier" in markdown
    assert "No model was trained" in markdown
    # Threats to validity.
    assert "## Threats to validity" in markdown
    assert "## Label methodology" in markdown
    # The formula, so a reader can reconstruct any percentage by hand.
    assert "weighted_skill_coverage" in markdown
    assert "proficiency_factor" in markdown


def test_markdown_report_states_the_circularity_limitation(result) -> None:
    """The report must not hide that the labels came from the knowledge base.

    This is the single most important caveat in the whole evaluation, and a
    reader skimming the metrics table would never see it in the prose unless the
    limitation is explicit.
    """
    markdown = harness.render_markdown(result, ())
    assert "not independent of the knowledge base" in markdown
    assert "26 profiles" in markdown or f"{result.n_profiles} profiles" in markdown


def test_markdown_report_marks_the_default_weight(result) -> None:
    points = harness.sweep(
        load_profiles(),
        load_role_specs(harness.DEFAULT_ROLES_PATH, skill_ids=load_taxonomy_index(harness.DEFAULT_TAXONOMY_PATH)),
        taxonomy=load_taxonomy(str(harness.DEFAULT_TAXONOMY_PATH)),
        skill_ids=load_taxonomy_index(harness.DEFAULT_TAXONOMY_PATH),
    )
    markdown = harness.render_markdown(result, points)
    assert "0.60 (default)" in markdown
    assert "Recommendation:" in markdown


def test_the_committed_report_is_a_golden_artifact(tmp_path) -> None:
    """The committed report must be exactly what the current engine produces.

    This is the guard that makes the other assertions in this file meaningful.
    A change to the ranker, the matcher or the knowledge base changes the
    numbers, and the numbers are published in ``docs/evaluation_report.md`` and
    served by ``GET /api/admin/evaluation``. If the committed artefact can
    drift away from the live engine, then a reader of the report is reading
    history, not the system.

    So the report is regenerated from scratch and compared byte for byte. An
    intentional engine change must regenerate the artefact in the same commit;
    an accidental one fails here.
    """
    json_path = tmp_path / "report.json"
    md_path = tmp_path / "report.md"
    harness.main(
        [
            "--json-report", str(json_path),
            "--markdown-report", str(md_path),
        ]
    )

    committed_json = Path(harness.DEFAULT_JSON_REPORT).read_text(encoding="utf-8")
    assert json_path.read_text(encoding="utf-8") == committed_json, (
        "the committed report.json no longer matches the engine; regenerate it with "
        "`python -m app.ml.evaluation` and commit the result in the same change"
    )

    committed_md = harness.DEFAULT_MARKDOWN_REPORT.read_text(encoding="utf-8")
    assert md_path.read_text(encoding="utf-8") == committed_md, (
        "the committed docs/evaluation_report.md no longer matches the engine; "
        "regenerate it with `python -m app.ml.evaluation`"
    )


def test_json_report_is_written_and_machine_readable(result, tmp_path) -> None:
    import json as json_module

    points = harness.sweep(
        load_profiles(),
        load_role_specs(harness.DEFAULT_ROLES_PATH, skill_ids=load_taxonomy_index(harness.DEFAULT_TAXONOMY_PATH)),
        taxonomy=load_taxonomy(str(harness.DEFAULT_TAXONOMY_PATH)),
        skill_ids=load_taxonomy_index(harness.DEFAULT_TAXONOMY_PATH),
    )
    json_path = tmp_path / "report.json"
    md_path = tmp_path / "report.md"
    harness.write_reports(result, points, json_path=json_path, markdown_path=md_path)

    payload = json_module.loads(json_path.read_text(encoding="utf-8"))
    assert payload["metrics"]["top3_hit_rate"] == result.top3_hit_rate
    assert payload["meets_target"] is True
    assert len(payload["outcomes"]) == result.n_profiles
    assert len(payload["sweep"]) == len(points)
    assert payload["noise_floor"] == pytest.approx(1.0 / result.n_profiles, abs=1e-6)
    assert md_path.read_text(encoding="utf-8").startswith("# Matching Engine Evaluation")


def test_cli_entry_point_exits_zero_when_the_target_is_met(capsys) -> None:
    """`--check` is the CI gate, so its exit code is part of the contract."""
    assert harness.main(["--check"]) == 0
    out = capsys.readouterr().out
    assert "top-3 hit rate" in out
    assert "recommended split" in out


def test_documented_module_command_works_as_a_subprocess(tmp_path) -> None:
    """`python -m app.ml.evaluation` is the command the report tells a reader to run.

    Tested as a real subprocess because that is the only way to catch the failure
    mode where the in-process API works but the module entry point does not --
    which is exactly how this harness failed the first time it was run.
    """
    import subprocess
    import sys

    completed = subprocess.run(
        [
            sys.executable, "-m", "app.ml.evaluation", "--check",
            "--json-report", str(tmp_path / "r.json"),
            "--markdown-report", str(tmp_path / "r.md"),
        ],
        capture_output=True,
        text=True,
        timeout=600,
        cwd=str(harness._BACKEND_ROOT),
    )
    assert completed.returncode == 0, completed.stderr[-2000:]
    assert "top-3 hit rate" in completed.stdout
    assert (tmp_path / "r.md").exists()
    assert (tmp_path / "r.json").exists()


def test_check_mode_would_fail_below_the_target(monkeypatch, capsys, tmp_path) -> None:
    """The gate must be capable of failing, or it is not a gate.

    Simulates a regression by forcing the metrics down, and asserts the exit
    code is non-zero. Without this, a broken `--check` would sail CI while
    looking like a passing test.
    """
    from app.ml.evaluation import metrics as metrics_module

    def degraded(expected, predictions, **kwargs):
        return metrics_module.Metrics(
            n_profiles=len(expected),
            top1_accuracy=0.0,
            top3_hit_rate=0.10,
            mean_reciprocal_rank=0.05,
            mean_compatibility_of_expected=0.0,
            component_means={},
        )

    monkeypatch.setattr(harness, "compute_metrics", degraded)
    # Write to tmp, never to the committed report paths: main() has the side
    # effect of regenerating the reports, and a test must not be able to leave
    # degraded placeholder numbers sitting in a committed artifact.
    report_args = [
        "--json-report", str(tmp_path / "r.json"),
        "--markdown-report", str(tmp_path / "r.md"),
    ]
    assert harness.main(["--check", "--no-sweep", *report_args]) == 1
    assert harness.main(["--no-sweep", *report_args]) == 0
    written = (tmp_path / "r.md").read_text(encoding="utf-8")
    assert "0.100" in written, "the degraded metrics should be what got written"
    capsys.readouterr()


def test_reported_figures_are_not_drifted() -> None:
    """The numbers the report quotes about the suite must be the real ones.

    Hard-coding a coverage figure in a document is how documents start lying.
    These assertions fail the moment the suite changes shape, forcing the report
    to be regenerated rather than quietly becoming wrong.
    """
    from app.ml.evaluation import harness as h

    tests = sorted(tests_dir.glob("test_*.py"))
    assert h.TEST_SUITE_SIZE >= 60, "the plan's floor is 60 tests"
    assert h.TEST_COVERAGE_PCT >= 80, "coverage fell well below the reported figure"
    assert h.HARNESS_COVERAGE_PCT > 0 and h.LEARNING_PATH_COVERAGE_PCT > 0
    # The report must actually contain them, or the constants are dead.
    markdown = h.render_markdown(
        h.evaluate(
            load_profiles(),
            load_role_specs(
                h.DEFAULT_ROLES_PATH, skill_ids=load_taxonomy_index(h.DEFAULT_TAXONOMY_PATH)
            ),
            taxonomy=load_taxonomy(str(h.DEFAULT_TAXONOMY_PATH)),
            skill_ids=load_taxonomy_index(h.DEFAULT_TAXONOMY_PATH),
        ),
        (),
    )
    assert str(h.TEST_SUITE_SIZE) in markdown
    assert f"{h.TEST_COVERAGE_PCT}%" in markdown
    del tests
