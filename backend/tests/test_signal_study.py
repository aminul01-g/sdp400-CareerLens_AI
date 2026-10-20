"""The context signals, measured.

``docs/limitations.md`` used to say that nothing measured whether the context
signals helped. The signals existed, they were unit-tested against
hand-computed multipliers, and they had never been observed changing a
ranking. This file is that observation.

Four properties are checked here, and they are deliberately different in kind
from the unit tests in ``test_signals.py``:

1. **The pairs are honest.** The two variants of a pair must declare
   identical skills, the control must declare nothing, and the loader must
   reject a pair that breaks either rule. Without these, a result could be
   manufactured by editing a label file.
2. **The signal is isolated.** The two variants of a pair must produce the
   same TF-IDF vector, so that every difference in the outcome is
   attributable to the signals and nothing else.
3. **The signals do what they claim.** Every pair must move the margin toward
   the expected role, and no pair's rank may get worse.
4. **Silence is neutral.** A user who states nothing must be scored exactly as
   the engine scored them before the signals existed.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from app.ml.evaluation import harness, signal_study
from app.ml.evaluation.harness import (
    load_profiles,
    load_role_specs,
    load_seniorities,
    load_taxonomy_index,
)
from app.ml.evaluation.signal_study import (
    EVALUATION_TODAY,
    SignalStudyError,
    load_signal_profiles,
)
from app.ml.taxonomy import load as load_taxonomy

_ROLES_PATH = harness.DEFAULT_ROLES_PATH
_TAXONOMY_PATH = harness.DEFAULT_TAXONOMY_PATH
_SIGNAL_PATH = harness.DEFAULT_SIGNAL_PROFILES_PATH


@pytest.fixture(scope="module")
def knowledge_base():
    taxonomy = load_taxonomy(str(_TAXONOMY_PATH))
    skill_ids = load_taxonomy_index(_TAXONOMY_PATH)
    role_specs = load_role_specs(_ROLES_PATH, skill_ids=skill_ids)
    seniorities = load_seniorities(_ROLES_PATH)
    return taxonomy, skill_ids, role_specs, seniorities


@pytest.fixture(scope="module")
def pairs():
    return load_signal_profiles(_SIGNAL_PATH)


@pytest.fixture(scope="module")
def study(pairs, knowledge_base):
    taxonomy, skill_ids, role_specs, seniorities = knowledge_base
    return harness.run_signal_study(
        pairs,
        role_specs,
        taxonomy=taxonomy,
        skill_ids=skill_ids,
        role_seniorities=seniorities,
    )


# --------------------------------------------------------------------------- #
# the pairs are honest
# --------------------------------------------------------------------------- #


def test_the_study_covers_all_three_kinds_of_signal(pairs) -> None:
    kinds = {pair.kind for pair in pairs}
    assert kinds == {"level", "recency", "depth"}


def test_the_study_has_enough_pairs_to_mean_something(pairs) -> None:
    assert len(pairs) >= 9


def test_the_two_variants_of_a_pair_declare_identical_skills(pairs) -> None:
    for pair in pairs:
        assert pair.with_signals.skills == pair.without_signals.skills, pair.pair_id


def test_the_control_variant_declares_nothing(pairs) -> None:
    for pair in pairs:
        assert not pair.without_signals.declares_a_signal, pair.pair_id
        assert pair.with_signals.declares_a_signal, pair.pair_id


def test_every_pair_names_two_distinct_roles_that_exist(pairs, knowledge_base) -> None:
    _, _, role_specs, _ = knowledge_base
    slugs = {spec.slug for spec in role_specs}
    for pair in pairs:
        assert pair.expected_role != pair.competing_role, pair.pair_id
        assert pair.expected_role in slugs, pair.pair_id
        assert pair.competing_role in slugs, pair.pair_id


def test_the_label_file_is_committed_and_not_empty() -> None:
    assert _SIGNAL_PATH.exists()
    assert _SIGNAL_PATH.read_text(encoding="utf-8").strip()


def test_the_label_file_is_reproducible_from_the_generator() -> None:
    """The data file must be exactly what the documented rule produces.

    Without this, the pairs could be hand-edited to produce a better number,
    and the generator's rule would be a fiction.
    """
    from scripts.make_signal_profiles import build_records, load_roles

    records = build_records(load_roles())
    expected = "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n"
    assert _SIGNAL_PATH.read_text(encoding="utf-8") == expected, (
        "signal_profiles.jsonl no longer matches scripts/make_signal_profiles.py; "
        "regenerate it with `python -m scripts.make_signal_profiles`"
    )


# --------------------------------------------------------------------------- #
# the loader rejects a rigged pair
# --------------------------------------------------------------------------- #


def _write(tmp_path: Path, records: list[dict]) -> Path:
    path = tmp_path / "signal_profiles.jsonl"
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )
    return path


def _base_records() -> list[dict]:
    return [
        {
            "id": "X1-with_signals",
            "pair_id": "X1",
            "variant": "with_signals",
            "name": "A candidate",
            "expected_role": "data-scientist",
            "expected_family": "Data Science",
            "competing_role": "senior-data-scientist",
            "signal_kind": "level",
            "skills": [{"skill_slug": "python", "proficiency": 4}],
            "seniority": "Senior",
            "years_experience": 8,
            "rationale": "A candidate.",
        },
        {
            "id": "X1-without_signals",
            "pair_id": "X1",
            "variant": "without_signals",
            "name": "A candidate",
            "expected_role": "data-scientist",
            "expected_family": "Data Science",
            "competing_role": "senior-data-scientist",
            "signal_kind": "level",
            "skills": [{"skill_slug": "python", "proficiency": 4}],
            "rationale": "A candidate.",
        },
    ]


def test_the_loader_accepts_a_well_formed_pair(tmp_path) -> None:
    pairs = load_signal_profiles(_write(tmp_path, _base_records()))
    assert len(pairs) == 1
    assert pairs[0].pair_id == "X1"


def test_the_loader_rejects_a_pair_whose_variants_differ(tmp_path) -> None:
    records = _base_records()
    records[1]["skills"] = [{"skill_slug": "python", "proficiency": 5}]
    with pytest.raises(SignalStudyError, match="identical skills"):
        load_signal_profiles(_write(tmp_path, records))


def test_the_loader_rejects_a_control_that_declares_a_signal(tmp_path) -> None:
    records = _base_records()
    records[1]["seniority"] = "Senior"
    with pytest.raises(SignalStudyError, match="must be silent"):
        load_signal_profiles(_write(tmp_path, records))


def test_the_loader_rejects_a_pair_with_only_one_variant(tmp_path) -> None:
    records = _base_records()[:1]
    with pytest.raises(SignalStudyError, match="missing"):
        load_signal_profiles(_write(tmp_path, records))


def test_the_loader_rejects_an_unknown_signal_kind(tmp_path) -> None:
    records = _base_records()
    records[0]["signal_kind"] = "vibes"
    with pytest.raises(SignalStudyError, match="signal_kind"):
        load_signal_profiles(_write(tmp_path, records))


def test_the_loader_rejects_a_malformed_date(tmp_path) -> None:
    records = _base_records()
    records[0]["skill_signals"] = [
        {"skill_slug": "python", "last_used_at": "the nineties"}
    ]
    with pytest.raises(SignalStudyError, match="invalid ISO date"):
        load_signal_profiles(_write(tmp_path, records))


def test_the_loader_rejects_a_signal_for_a_skill_the_profile_lacks(tmp_path) -> None:
    records = _base_records()
    records[0]["skill_signals"] = [{"skill_slug": "rust", "last_used_at": "2026-01-01"}]
    with pytest.raises(SignalStudyError, match="does not declare"):
        load_signal_profiles(_write(tmp_path, records))


def test_the_loader_rejects_a_level_pair_with_no_level(tmp_path) -> None:
    records = _base_records()
    records[0].pop("seniority")
    with pytest.raises(SignalStudyError, match="must declare a level"):
        load_signal_profiles(_write(tmp_path, records))


def test_the_loader_rejects_a_recency_pair_with_no_date(tmp_path) -> None:
    records = _base_records()
    for record in records:
        record["signal_kind"] = "recency"
    # The pair declares a signal — years of experience — but no date, so the
    # recency-specific rule is what rejects it.
    records[0].pop("seniority")
    records[0]["years_experience"] = 8
    with pytest.raises(SignalStudyError, match="last-used date"):
        load_signal_profiles(_write(tmp_path, records))


# --------------------------------------------------------------------------- #
# the signal is isolated
# --------------------------------------------------------------------------- #


def test_the_two_variants_of_a_pair_produce_the_same_text(pairs, knowledge_base) -> None:
    """The isolation property: only the signal multipliers may differ."""
    taxonomy, skill_ids, _, _ = knowledge_base
    for pair in pairs:
        with_text = signal_study.build_snapshot(pair.with_signals, skill_ids, taxonomy)
        without_text = signal_study.build_snapshot(pair.without_signals, skill_ids, taxonomy)
        assert with_text.profile_text == without_text.profile_text, pair.pair_id


# --------------------------------------------------------------------------- #
# the signals do what they claim
# --------------------------------------------------------------------------- #


def test_every_pair_moves_the_margin_toward_the_expected_role(study) -> None:
    failures = [outcome.pair_id for outcome in study.pairs if not outcome.directional_success]
    assert not failures, f"pairs that did not move toward the expected role: {failures}"
    assert study.directional_successes == study.n_pairs


def test_no_pairs_rank_gets_worse(study) -> None:
    assert study.rank_regressions == 0, [
        outcome.pair_id for outcome in study.pairs if outcome.rank_regressed
    ]


def test_some_pairs_actually_change_the_recommendation(study) -> None:
    """The signals must be able to change the answer, not just nudge it."""
    assert study.rank_improvements >= 1


def test_the_signals_can_only_lower_a_score(study) -> None:
    """A declared signal must never inflate the user's own score.

    The level fit and the recency and depth factors are all multipliers of at
    most 1.0, so this is guaranteed by the arithmetic. The test exists so that
    a future change to the engine cannot quietly break the guarantee.
    """
    for outcome in study.pairs:
        assert outcome.with_compatibility <= outcome.without_compatibility + 1e-9, (
            outcome.pair_id
        )
        assert outcome.with_competing_compatibility <= outcome.without_competing_compatibility + 1e-9, (
            outcome.pair_id
        )


def test_the_expected_role_keeps_its_score_in_every_pair(study) -> None:
    """The construction keeps the expected role's coverage untouched.

    The candidate's own skills are all current, so the only discounted skills
    in the profile belong to the competing role. That is what makes the margin
    attributable to the signal rather than to a general loss of points.
    """
    for outcome in study.pairs:
        assert outcome.with_compatibility == pytest.approx(
            outcome.without_compatibility, abs=1e-9
        ), outcome.pair_id


def test_the_level_fit_moves_more_than_the_recency_signal(study) -> None:
    """The level fit is a 8% band discount; recency is bounded at 30% per skill.

    Which of the two moves a score more is a property of the design, not a
    discovery, and the test records it so a change to either constant is
    visible.
    """
    level = study.per_kind["level"]["mean_margin_delta"]
    recency = study.per_kind["recency"]["mean_margin_delta"]
    assert level > recency


def test_the_study_result_serialises(pairs, knowledge_base) -> None:
    taxonomy, skill_ids, role_specs, seniorities = knowledge_base
    result = harness.run_signal_study(
        pairs,
        role_specs,
        taxonomy=taxonomy,
        skill_ids=skill_ids,
        role_seniorities=seniorities,
    )
    payload = result.to_dict()
    assert payload["n_pairs"] == len(pairs)
    assert payload["directional_success_rate"] == 1.0
    assert payload["is_clean"] is True


# --------------------------------------------------------------------------- #
# silence is neutral
# --------------------------------------------------------------------------- #


def test_a_user_who_states_nothing_is_scored_exactly_as_before(knowledge_base) -> None:
    """The engine's rule that absence is neutral, checked over the whole set.

    Every one of the 26 labelled profiles is scored with the recency half of
    the signal machinery off and on. The two rankings must be identical, down
    to the sixth decimal, or every existing user's shortlist would change
    under them for no reason.
    """
    taxonomy, skill_ids, role_specs, seniorities = knowledge_base
    silence = harness.run_silence_check(
        load_profiles(),
        role_specs,
        taxonomy=taxonomy,
        skill_ids=skill_ids,
        role_seniorities=seniorities,
    )
    assert silence.is_neutral, f"profiles scored differently: {silence.mismatches}"
    assert silence.identical == silence.n_profiles
    assert silence.n_profiles == 26


def test_the_reference_date_matches_the_report_date() -> None:
    """The study's clock and the report's stamp must not drift apart."""
    assert date.fromisoformat(harness.GENERATED_AT) == EVALUATION_TODAY


# --------------------------------------------------------------------------- #
# the report
# --------------------------------------------------------------------------- #


def test_the_report_carries_the_signal_study() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        md_path = Path(tmp) / "report.md"
        json_path = Path(tmp) / "report.json"
        harness.main(
            ["--json-report", str(json_path), "--markdown-report", str(md_path)]
        )
        markdown = md_path.read_text(encoding="utf-8")
        assert "## Context signals" in markdown
        assert "Silence is neutral" in markdown
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        assert payload["signal_study"]["n_pairs"] == 12
        assert payload["silence_check"]["is_neutral"] is True
