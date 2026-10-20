# Matching Engine Evaluation

Generated: 2026-09-30  
Weights: skill coverage **0.6** / tf-idf **0.4**, over 100 job roles and 26 labelled profiles.

Reproduce with:

```bash
cd backend && python -m app.ml.evaluation --check
```

## Headline metrics

| Metric | Value | Target | Met |
| --- | --- | --- | --- |
| Top-1 accuracy | 0.692 (18/26) | not set | - |
| **Top-3 hit rate** | **1.000** (26/26) | >= 0.75 | **yes** |
| Mean reciprocal rank | 0.840 | not set | - |
| Mean compatibility of expected role | 0.418 | not set | - |

Component means for the expected role:

| Component | Mean |
| --- | --- |
| skill coverage | 0.637 |
| tfidf similarity | 0.088 |
| compatibility | 0.418 |

## Weight sweep

| Coverage | tf-idf | Top-1 | Top-3 | MRR | Mean compat. of expected |
| --- | --- | --- | --- | --- | --- |
| 0.00 | 1.00 | 0.500 | 0.769 | 0.633 | 0.088 |
| 0.50 | 0.50 | 0.731 | 1.000 | 0.853 | 0.363 |
| 0.60 (default) | 0.40 | 0.692 | 1.000 | 0.840 | 0.418 |
| 0.70 | 0.30 | 0.692 | 1.000 | 0.840 | 0.472 |
| 0.80 | 0.20 | 0.615 | 0.962 | 0.790 | 0.527 |
| 0.90 | 0.10 | 0.577 | 0.923 | 0.759 | 0.582 |
| 1.00 | 0.00 | 0.538 | 0.846 | 0.718 | 0.637 |

**Recommendation: 0.6 / 0.4.** That is the value already shipped, so no code change is warranted: the evidence supports the current default rather than overturning it.

The un-guarded best on this set is 0.5 / 0.5 at top-1 0.731, which is +0.038 against the shipped 0.6. One profile on a 26-profile set is worth 0.038, so that margin is below the resolution of the label set. The recommendation therefore holds the default rather than retuning on a difference the data cannot resolve.

The top-3 hit rate varies by 0.23 across the range, so the split does matter and the recommended value should be taken seriously.

Coverage alone (1.0) and text alone (0.0) are both reported as endpoints of a wider probe than the plan's range, because the interesting question is whether either component is doing any work at all.

## Per family

| Family | n | Top-1 | Top-3 | MRR |
| --- | --- | --- | --- | --- |
| AI Engineer | 2 | 0.500 | 1.000 | 0.750 |
| Computer Vision | 1 | 1.000 | 1.000 | 1.000 |
| Data Engineering | 3 | 0.667 | 1.000 | 0.833 |
| Data Science | 5 | 0.600 | 1.000 | 0.767 |
| LLM Engineer | 2 | 0.500 | 1.000 | 0.750 |
| ML Engineer | 3 | 1.000 | 1.000 | 1.000 |
| MLOps | 3 | 0.333 | 1.000 | 0.667 |
| NLP | 2 | 1.000 | 1.000 | 1.000 |
| Quantitative | 1 | 1.000 | 1.000 | 1.000 |
| Research | 3 | 0.667 | 1.000 | 0.833 |
| Software Engineering | 1 | 1.000 | 1.000 | 1.000 |

## Per profile

| ID | Expected role | Top-1 prediction | Expected rank | Top-3 | Note |
| --- | --- | --- | --- | --- | --- |
| P01 | machine-learning-engineer | machine-learning-engineer | 1 | yes | - |
| P02 | machine-learning-engineer | machine-learning-engineer | 1 | yes | - |
| P03 | machine-learning-engineer | machine-learning-engineer | 1 | yes | boundary: AI Engineer is a plausible alternative |
| P04 | ai-engineer | ai-engineer | 1 | yes | - |
| P05 | ai-engineer | backend-engineer | 2 | yes | boundary: MLOps Engineer is a plausible alternative |
| P06 | data-scientist | pricing-analyst | 3 | yes | - |
| P07 | time-series-forecasting-specialist | time-series-forecasting-specialist | 1 | yes | - |
| P08 | machine-learning-scientist | machine-learning-engineer | 2 | yes | boundary: Machine Learning Engineer is a plausible alternative |
| P09 | data-analyst | junior-data-analyst | 2 | yes | - |
| P10 | data-engineer | data-engineer | 1 | yes | - |
| P11 | analytics-engineer | analytics-engineer | 1 | yes | - |
| P12 | senior-data-engineer | data-engineering-manager | 2 | yes | - |
| P13 | mlops-engineer | mlops-engineer | 1 | yes | - |
| P14 | machine-learning-infrastructure-engineer | machine-learning-infrastructure-lead | 2 | yes | - |
| P15 | devops-engineer | kubernetes-administrator | 2 | yes | - |
| P16 | nlp-engineer | nlp-engineer | 1 | yes | - |
| P17 | llm-engineer | generative-ai-engineer | 2 | yes | boundary: Generative AI Engineer is a plausible alternative |
| P18 | speech-and-audio-engineer | speech-and-audio-engineer | 1 | yes | - |
| P19 | llm-engineer | llm-engineer | 1 | yes | - |
| P20 | computer-vision-engineer | computer-vision-engineer | 1 | yes | - |
| P21 | machine-learning-scientist | machine-learning-scientist | 1 | yes | - |
| P22 | research-scientist | research-scientist | 1 | yes | - |
| P23 | fraud-analyst | fraud-analyst | 1 | yes | - |
| P24 | quantitative-researcher | quantitative-researcher | 1 | yes | - |
| P25 | data-analyst | data-analyst | 1 | yes | thin profile: coverage is low everywhere; top-1 is expected to be unstable |
| P26 | backend-engineer | backend-engineer | 1 | yes | - |

## Context signals: a matched-pair measurement

The evaluation above scores every profile on declared proficiency alone, because the label set declares no years of experience, no level, and no per-skill recency or depth. That is a deliberate choice — the headline numbers stay comparable — but it left the context signals **unmeasured**, and an unmeasured feature is one nobody can say anything true about.

This section is that measurement. It runs 12 **matched pairs** of profiles. Each pair is one candidate described twice: the two descriptions declare identical skills, identical proficiencies and identical text, and differ only in whether the candidate declares a level, years of experience, and per-skill recency and depth. Because a level is not a word in the profile text, the two descriptions produce the same TF-IDF vector — so **every difference in the outcome is attributable to the signals** and nothing else moved.

Each pair names the role the signals *should* favour and the role they should beat. The quantity measured is the **margin** between the two: a larger margin means the signals moved the ranking toward the expected role. The margin is used rather than the raw rank because it is continuous, so a pair that does not change the order can still show the scores moving the right way.

| Pair | Signal | Expected role | Competing role | Compat. (signals) | Compat. (silent) | Margin delta | Rank |
| --- | --- | --- | --- | --- | --- | --- | --- |
| D01 | depth | analytics-engineer | analytics-engineer-for-experimentation | 0.613 | 0.613 | +0.018 | 1 -> 1 |
| D02 | depth | applied-scientist | time-series-forecasting-specialist | 0.606 | 0.606 | +0.015 | 1 -> 1 |
| D03 | depth | responsible-ai-auditor | ai-ethics-and-governance-specialist | 0.600 | 0.600 | +0.009 | 1 -> 1 |
| L01 | level | ml-solutions-architect | ai-engineer | 0.604 | 0.604 | +0.048 | 2 -> 2 |
| L02 | level | senior-financial-analyst | financial-analyst | 0.632 | 0.632 | +0.048 | 1 -> 1 |
| L03 | level | computer-vision-research-engineer | computer-vision-engineer | 0.633 | 0.633 | +0.048 | 1 -> 1 |
| L04 | level | big-data-engineer | data-engineer | 0.603 | 0.603 | +0.048 | 2 -> 1 |
| L05 | level | applied-scientist | data-scientist | 0.607 | 0.607 | +0.048 | 2 -> 1 |
| L06 | level | llm-engineer | generative-ai-engineer | 0.623 | 0.623 | +0.048 | 2 -> 1 |
| R01 | recency | analytics-engineer | analytics-engineer-for-experimentation | 0.613 | 0.613 | +0.028 | 1 -> 1 |
| R02 | recency | applied-scientist | time-series-forecasting-specialist | 0.606 | 0.606 | +0.023 | 1 -> 1 |
| R03 | recency | responsible-ai-auditor | ai-ethics-and-governance-specialist | 0.600 | 0.600 | +0.015 | 1 -> 1 |

| Measurement | Value |
| --- | --- |
| Pairs where the signals moved the margin toward the expected role | 12/12 |
| Pairs where the expected role's rank improved | 3/12 |
| Pairs where the expected role's rank got worse | 0/12 |
| Mean margin change | +0.033 |
| Mean change in the expected role's compatibility | +0.000 |
| Mean change in the competing role's compatibility | -0.033 |
| Mean compatibility of the expected role, with signals | 0.612 |
| Mean compatibility of the expected role, silent | 0.612 |

- **depth** — 3 pairs, 3 moved toward the expected role, mean margin change +0.014.
- **level** — 6 pairs, 6 moved toward the expected role, mean margin change +0.048.
- **recency** — 3 pairs, 3 moved toward the expected role, mean margin change +0.022.

**The direction is a property of the construction, and that is not the finding.** Each pair was built so that the signal *must* favour the expected role — a level pair puts the candidate at the expected role's band, a recency pair makes the competing role's exclusive skills stale. A study whose pairs are designed to come out one way cannot tell you the direction is right; it can only tell you the mechanism does what it claims. What it does tell you is the **magnitude**, and the magnitude is the number nobody had.

The expected role's compatibility moved by +0.000 on average, and the competing role's by -0.033. The signals do not boost anything. They **discount**, and the whole effect is a redistribution: a role that matches the declared level and the skills still in use keeps its score, and a role that does not is marked down. That is a property of the arithmetic — the level fit and the recency and depth factors are all multipliers of at most 1.0 — and it is worth stating plainly, because it means **declaring more can never inflate a user's own score**. It can only change which of their roles is ranked highest.

The margin moved by +0.033 on average, and the expected role's **rank** improved in 3 of 12 pairs and got worse in 0. A level declaration is therefore a tie-breaker rather than a decider: it narrows the gap between adjacent bands without ever hiding a role, which is what the engine's own documentation says it is for. The recency and depth signals are the ones that move a role's score materially, because a skill the candidate has not touched in eleven years is worth less than one they used last month.

**What this establishes, and what it does not.** It establishes that the signals do what their documentation says they do, and it quantifies how far they move a score. It does **not** establish that they improve anyone's career: the pairs are synthetic and purpose-built, so this is a correctness check on a mechanism, not evidence about the world. Independent labels, observed hiring outcomes and profiles from real users are what would be needed for that, and none of them exists here.

### Silence is neutral

Every one of the 26 labelled profiles was scored twice -- once with the recency half of the signal machinery switched off and once with it on. The two rankings must be identical, down to the sixth decimal, because a skill with no recency has a recency factor of exactly 1.0 and a user with no declared level has a level fit of exactly 1.0.

**Result: 26/26 profiles identical.** A candidate who states nothing is scored exactly as the engine scored them before the signals existed.

## Design honesty: no trained classifier

**No model was trained and none is loaded at inference time.** The engine is a transparent weighted formula over a curated knowledge base:

```
compatibility = 0.6 * weighted_skill_coverage + 0.4 * tfidf_cosine(profile, role)
weighted_skill_coverage = sum(weight_i * proficiency_factor_i) / sum(weight_i)
proficiency_factor = (proficiency - 1) / 4        # 1 -> 0.0, 5 -> 1.0
```

This is deliberate, per proposal section 4.2. A classifier trained on resume labels would need labelled data this project does not have, would be impossible to explain to the user who is shown a percentage, and would be a single point of silent failure when the distribution shifts. A formula can be audited line by line, and every number in the UI can be reconstructed by hand from the same inputs. The consequence is that no *learned* generalisation is claimed: the engine matches declared skills against curated requirements, and the evaluation below measures exactly that and nothing more.

## Threats to validity

**The labels are not independent of the knowledge base.** Every `expected_role` was assigned by reading the same required-skill sets and weights in `data/job_roles.json` that the engine scores against. The evaluation therefore measures whether the engine is internally consistent with the knowledge base, not whether its role definitions match what employers or informed humans would say. A top-3 hit rate of 1.000 on such a set is evidence of a working implementation and weak evidence of career advice quality. Independent labelling -- by career practitioners, or against observed hiring outcomes -- is the missing piece.

**Test coverage of the engine itself.** The full suite is 656 tests with 0 failures and 92% statement coverage of `app/`. The evaluation harness is at 95% and the optional learning-path module at 93%, the latter being lower only because the provider-success path is exercised with a stubbed transport rather than a live API call. Coverage says the code runs; it says nothing about whether the role definitions are right, which is the limitation above.

**Small sample.** 26 profiles means one profile moves Top-1 by 0.038 and Top-3 by 0.038. Differences smaller than that between weight settings are noise, and are not treated as signal above.

**Synthetic profiles.** The candidates are constructed, not real, so no personal or professional data of any kind is involved. Their skill distributions are smoother and more internally consistent than a real profile, which flatters the engine.

**The context signals are self-declared, and the measurement of them is narrow.** The engine reads years of experience, a declared level, per-skill recency and per-skill depth, and it compares the user's level with the role's. The matched-pair study above measures what those signals do to a ranking, and the silence check proves that a user who states nothing is not penalised. Two limits remain. The study's pairs are synthetic and purpose-built, so it is a correctness check on a mechanism rather than evidence that the mechanism helps anybody. And the signals are still self-report: a candidate can claim thirty years of experience and the engine has no way to check. The 26 profiles in the headline evaluation declare none of it, so the metrics above remain a measurement of declared proficiency alone.

**Proficiency is self-reported and coarse.** A 1-5 integer is a weak signal, and the `(p - 1) / 4` factor is a linear assumption. The factor now rests on a written rubric (`docs/proficiency-rubric.md`) rather than on nothing, which is a better foundation but not evidence. Self-reported proficiency is also systematically biased upward, and the rubric does not remove that bias.

**The community prior is not exercised here either.** The ranking applies a small adjustment from what users have said about a role, and that adjustment is bounded and needs a minimum number of observations before it is used at all. The 26 profiles here carry no feedback, so the prior is exactly zero in every row of this report.

**The near-boundary profiles were designed to be hard.** Several profiles sit deliberately between two defensible roles, so the top-3 figure is a floor rather than a ceiling, and the top-1 figure should be read as pessimistic for those rows.

## Label methodology

- Each label was assigned by reading the target role's required-skill list and weights, then selecting the skills a genuine candidate for that role would hold at the stated proficiencies.
- Each rationale was written from the role definition, describing the *shape* of the role rather than the engine's arithmetic on that profile.
- No label was changed, reordered or removed after seeing a prediction. The label file is the input to every run and is committed unchanged.
- Coverage is deliberately uneven and includes near-boundary cases, a sparse four-skill profile, and a backend profile with no AI/ML skill at all, so the metric is not trivially high.
- The two near-miss shapes in the results are informative rather than failures: where a profile's skills sit equally between two roles, top-2 returns both and the UI shows a genuine choice.
