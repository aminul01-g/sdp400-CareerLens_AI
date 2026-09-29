# Limitations

What this system cannot do, stated plainly. Every item here is a real property of
the shipped code, not a hedge.

The predecessor's version of this document described a different product. It was
rewritten for CareerLens AI against the code that exists, and
`scripts/verify_compliance.py` checks that no reference to the old product name
survives anywhere in the repository.

---

## 1. The recommendations are not career advice

**The engine has no notion of the labour market.** It matches declared skills
against a curated list of 82 roles. It does not know which roles are growing, which
are hiring in a given city, what they pay, or whether a role exists at all in a
particular industry. A role scoring 92% is one whose requirements you happen to
meet, not one you will find work in.

**A percentage is a similarity score, not a probability.** 70% means the weighted
skill coverage and text similarity produced 0.70. It is not "70% chance of getting
the job", and the UI should not be read that way.

## 2. The evaluation does not measure career outcomes

This is the most important limitation and it is worth being blunt about.

The 26 evaluation profiles were labelled by reading each role's required-skill set
and weights in `data/job_roles.json` — the same knowledge base the engine scores
against. The labels are therefore **not independent** of the system under test.
A top-3 hit rate of 1.000 on such a set is good evidence that the implementation
is internally consistent, and weak evidence that its role definitions match what
employers or informed humans would say.

Getting a real number would need labels from outside this project: career
practitioners ranking candidate profiles, or observed hiring outcomes. Neither
exists here. The number is reported because the plan requires one, not because it
settles the question.

Full detail, including the small sample and the flat weight sweep, is in
[`evaluation_report.md`](evaluation_report.md#threats-to-validity).

## 3. Skills are the only real signal

The engine reads a profile's skills, headline, bio, projects and education. It does
**not** model:

- **Years of experience or seniority.** Two profiles with identical skills and
  twenty years' difference in experience are indistinguishable. This is a real
  gap: a junior and a principal engineer with the same declared skills get the
  same score.
- **Recency.** A skill last used in 2004 is treated the same as one used last
  week. There is no decay.
- **Depth.** A skill listed at proficiency 5 and one listed at 5 contribute
  identically whether the user has written one line of it or a decade of it.
- **Industry, location or company.**

The consequence is that the shortlist is *directionally* useful and will not
distinguish two similar candidates for the same role.

## 4. Proficiency is self-reported and coarse

An integer from 1 to 5, entered by the user, with no verification. Self-reported
skill levels are systematically biased upward — people rate themselves against
peers, not against a rubric. The `(proficiency − 1) / 4` factor is a linear
assumption with no evidence behind it beyond "it is the simplest thing that is not
absurd".

## 5. CV extraction is shallow

- **No OCR.** A scanned or image-only PDF is rejected with a specific error. The
  user is told why; they are not given a silently empty result.
- **No layout understanding.** The extractor is a phrase matcher over the whole
  document. It cannot tell a skill listed under "Skills" from the same word inside
  a sentence describing something else.
- **No date parsing, no company recognition, no achievement quantification.** A CV
  becomes a bag of skill mentions and some text. Nothing else is extracted, so
  nothing else influences the score.
- **English only.** The spaCy model is `en_core_web_sm`.

The confirmation step exists precisely because of this: the extraction proposes,
the user disposes.

## 6. The knowledge base is small and hand-curated

151 skills, 82 roles, 16 families. That is enough to demonstrate the system and
not enough to be a career taxonomy. Missing from it: most industry-specific
technologies, every non-technical role, every regional market, and any role that
emerged after the curation date.

Adding a role is a JSON edit and a re-seed, so this is a data problem rather than
an architectural one — but a data problem that is currently unsolved.

## 7. Nothing is learned from use

There is no feedback loop. A user who corrects a detected skill, dismisses a
suggestion, or ignores a recommendation leaves no trace that affects a future
result. `feedback` is stored and readable by an admin, and that is all it does.

This is a direct consequence of choosing a formula over a trained model, and it is
a real cost: the system cannot improve, and it cannot get worse, either.

## 8. Operational limits

- **Single-region deployment.** One Render region, one Postgres instance. No
  read replicas, no multi-region failover.
- **The free tier is the free tier.** Render's free Postgres and free web service
  are sized for a demonstration. Sustained real use needs paid tiers, and the
  upload volume is on the container filesystem, which is ephemeral on some
  platforms.
- **No rate limiting** on authentication or generation endpoints. Brute-force
  protection on login is provided only by bcrypt's cost factor and JWT expiry.
- **No email verification, no password reset.** A user who forgets their password
  has no self-service route. This is a genuine gap for anything beyond a
  classroom project.
- **No audit log.** Admin actions are not recorded. `recommendation_run` is history
  of computations, not of administrative change.
- **Accessibility is untested against a real audit.** Semantic HTML and keyboard
  paths are used throughout, but no screen-reader pass or WCAG conformance check
  has been performed.

## 9. Not built

Named explicitly, because "not built" and "built but not shown" look identical in
a demo.

- **The optional LLM learning path is implemented but disabled** (`LLM_ENABLED=false`).
  It is reachable through one endpoint and degrades to deterministic local steps
  when no key is present. It has never been exercised against a live provider.
- **No mobile application.** The Next.js app is responsive and works on a phone
  viewport, but it is not a native app.
- **No social or networking features**, no job board, no employer side, no
  application tracking.
- **No localisation.** English only, throughout.

## 10. What would have to be true to trust it more

In rough order of value per unit of effort:

1. **Independent labels.** Have career practitioners or final-year students rank
   candidate profiles and compare with the engine. This is the single largest gap
   and needs no new code.
2. **A proficiency rubric.** A written definition per level, so "4" means the same
   thing to everyone and the linear factor has something behind it.
3. **Experience and recency.** The two missing signals that most affect whether a
   shortlist is useful in practice.
4. **Real usage data.** Whether users act on the shortlist is the only outcome
   metric that would settle question 1 empirically.
