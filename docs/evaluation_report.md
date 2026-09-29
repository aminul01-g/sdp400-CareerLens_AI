# Matching Engine Evaluation

Generated: 2026-09-30  
Weights: skill coverage **0.6** / tf-idf **0.4**, over 82 job roles and 26 labelled profiles.

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
| tfidf similarity | 0.089 |
| compatibility | 0.418 |

## Weight sweep

| Coverage | tf-idf | Top-1 | Top-3 | MRR | Mean compat. of expected |
| --- | --- | --- | --- | --- | --- |
| 0.00 | 1.00 | 0.500 | 0.808 | 0.637 | 0.089 |
| 0.50 | 0.50 | 0.731 | 1.000 | 0.859 | 0.363 |
| 0.60 (default) | 0.40 | 0.692 | 1.000 | 0.840 | 0.418 |
| 0.70 | 0.30 | 0.692 | 1.000 | 0.840 | 0.473 |
| 0.80 | 0.20 | 0.692 | 1.000 | 0.840 | 0.527 |
| 0.90 | 0.10 | 0.615 | 0.962 | 0.792 | 0.582 |
| 1.00 | 0.00 | 0.615 | 0.923 | 0.772 | 0.637 |

**Recommendation: 0.6 / 0.4.** That is the value already shipped, so no code change is warranted: the evidence supports the current default rather than overturning it.

The un-guarded best on this set is 0.5 / 0.5 at top-1 0.731, which is +0.038 against the shipped 0.6. One profile on a 26-profile set is worth 0.038, so that margin is below the resolution of the label set. The recommendation therefore holds the default rather than retuning on a difference the data cannot resolve.

The top-3 hit rate varies by 0.19 across the range, so the split does matter and the recommended value should be taken seriously.

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

**Test coverage of the engine itself.** The full suite is 392 tests with 0 failures and 92% statement coverage of `app/`. The evaluation harness is at 95% and the optional learning-path module at 93%, the latter being lower only because the provider-success path is exercised with a stubbed transport rather than a live API call. Coverage says the code runs; it says nothing about whether the role definitions are right, which is the limitation above.

**Small sample.** 26 profiles means one profile moves Top-1 by 0.038 and Top-3 by 0.038. Differences smaller than that between weight settings are noise, and are not treated as signal above.

**Synthetic profiles.** The candidates are constructed, not real, so no personal or professional data of any kind is involved. Their skill distributions are smoother and more internally consistent than a real profile, which flatters the engine.

**Skills are the only strong signal.** Real candidates signal seniority through years of experience, industry context and role history, none of which the engine models. Two profiles with identical skills and different real-world seniority are indistinguishable here.

**Proficiency is self-reported and coarse.** A 1-5 integer is a weak signal, and the `(p - 1) / 4` factor is a linear assumption with no evidence behind it. Self-reported proficiency is also systematically biased upward.

**The near-boundary profiles were designed to be hard.** Several profiles sit deliberately between two defensible roles, so the top-3 figure is a floor rather than a ceiling, and the top-1 figure should be read as pessimistic for those rows.

## Label methodology

- Each label was assigned by reading the target role's required-skill list and weights, then selecting the skills a genuine candidate for that role would hold at the stated proficiencies.
- Each rationale was written from the role definition, describing the *shape* of the role rather than the engine's arithmetic on that profile.
- No label was changed, reordered or removed after seeing a prediction. The label file is the input to every run and is committed unchanged.
- Coverage is deliberately uneven and includes near-boundary cases, a sparse four-skill profile, and a backend profile with no AI/ML skill at all, so the metric is not trivially high.
- The two near-miss shapes in the results are informative rather than failures: where a profile's skills sit equally between two roles, top-2 returns both and the UI shows a genuine choice.
