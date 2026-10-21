# Limitations

What this system cannot do, stated plainly. Every item here is a real property
of the shipped code, not a hedge.

The predecessor's version of this document described a different product. It was
rewritten for CareerLens AI against the code that exists, and
`scripts/verify_compliance.py` checks that no reference to the old product name
survives anywhere in the repository.

This is the third pass. The first two closed eleven items and reduced five
more. What remains is what is still true.

The optional AI layer added a fourth kind of limitation — a model can be
*confident* and still be wrong in a way a formula never is — so it has its own
section below. It is written as carefully as the rest of this document, because
a limitation nobody states is a limitation nobody is protected from.

---

## 1. The recommendations are not career advice

**The engine has no notion of the labour market.** It matches declared skills
and a profile text against a curated list of 100 roles. It does not know which
roles are growing, which hire in a given city, what they pay, or whether a
role exists at all in a particular industry. A role scoring 92% is one whose
requirements you happen to meet, not one you will find work in.

**A percentage is a similarity score, not a probability.** 70% means the
weighted skill coverage and the text similarity produced 0.70. It is not "70%
chance of getting the job", and the UI should not be read that way.

**The location field is not a market filter.** It is stored and displayed, but
nothing in the engine consults it, because there is no data about which roles
hire where. A user in a city with no AI/ML market sees the same shortlist as a
user in one with a large one.

## 2. What has not been measured

**The evaluation's labels are not independent.** The 26 profiles were labelled
by reading each role's required-skill set and weights in
`data/job_roles.json` — the same knowledge base the engine scores against. A
top-3 hit rate of 1.000 on such a set is good evidence that the implementation
is internally consistent, and weak evidence that its role definitions match
what employers or informed humans would say. A real number would need labels
from outside this project: career practitioners ranking candidate profiles, or
observed hiring outcomes. Neither exists here.

**The context signals are self-declared, and the measurement of them is
narrow.** The engine reads years of experience, a level, per-skill recency and
per-skill depth. A matched-pair study now measures what those signals do: a
candidate is described twelve times over, once with the signals and once
without, and the two descriptions differ in nothing else
(`docs/evaluation_report.md`). Every pair moved the margin toward the role the
signals were designed to favour, and a check over the whole label set confirms
that a user who states nothing is scored exactly as they would have been before
the signals existed.

That is a **correctness check on a mechanism, not evidence about the world.**
The pairs are synthetic and purpose-built, so the direction of each one is a
property of how it was built; only the magnitude and the effect on the ranking
are findings. The measured magnitude is small — the signals refine a ranking
rather than build one. And the signals remain self-report: a user can claim
thirty years of experience and the engine has no way to check.

**Proficiency is self-reported, and biased upward.** Proficiency is an integer
from 1 to 5, entered by the user, with no verification. Self-reported skill
levels are systematically biased upward — people rate themselves against peers,
not against a rubric. The rubric in [`proficiency-rubric.md`](proficiency-rubric.md)
makes "4" mean the same thing to everyone who enters it, which makes the claim
*comparable*; it does not make it *true*.

The `(proficiency − 1) / 4` factor is a linear assumption. It now rests on a
rubric defining the five levels as equal fifths of increasing independent
capability — a better foundation than nothing, still a linear map. A non-linear
one would need evidence this project does not have, and a curve fitted to 26
synthetic profiles would be worse than an honest straight line.

**The community prior is self-selected and self-reported.** The aggregate now
distinguishes *interest* — a role was saved, dismissed or found interesting —
from *outcome* — the user reports that they applied, were interviewed or were
offered the role, and an outcome counts for more than an opinion. The mechanism
is still a formula: a net favourability in `[-1, 1]`, applied as a multiplier
of at most 10%, so proposal §18.9 holds and the effect is reproducible by hand.

The prior reorders; it never excludes. A role everybody has dismissed is still
shown, still ranked, still explained. Below five observations it is exactly
zero, because three users' opinions are noise. And the outcomes it counts are
outcomes the user *says* happened: a candidate who applied and heard nothing
back records "applied", and the prior counts it as positive.

## 3. What the CV extractor does not see

The extractor is a phrase matcher over the text. It splits the document into
sections so a skill under **Skills** can be told apart from the same word
inside a project description, and it reads quantified claims out of the
sentences it finds. That is the limit of what it understands.

- **No OCR.** A scanned or image-only PDF is rejected with a specific error,
  so the user is told why rather than given a silently empty result. OCR is out
  of scope by proposal §11.
- **The achievements are counted, not understood.** "Reduced query time by 80%"
  is read as a percentage and "We saved $2M" as a currency amount, and the
  sentence is marked as the candidate's own work or the team's by its first
  pronoun. Nothing judges whether the achievement was impressive, and none of
  it affects the score: it is shown on the confirmation screen so the user can
  see what the document claims.
- **No understanding of the work.** The work history is read by matching the
  employer's name and the dates near it. It does not read the sentences about
  the job.
- **English only.** The spaCy model is `en_core_web_sm`.
- **The section splitter is a rule, not a model.** A CV with an unusual layout
  may be segmented oddly. The confirmation step exists precisely because of
  this: the extraction proposes, the user disposes.

## 4. What the data is

250 skills, 100 roles, 21 families, 1,234 weighted requirements. The catalogue
reaches outside AI/ML: a secondary school teacher, a registered nurse, an
accountant, a civil engineer, a quantity surveyor and a marketing manager are
real roles with real requirements, and `scripts/verify_compliance.py` fails if
they stop being.

It is still not a career taxonomy. Missing: most industry-specific
technologies, every regional market, and any role that emerged after the
curation date. Adding a role is a JSON edit and a re-seed, so this is a data
problem rather than an architectural one — but a data problem that is only
partly solved, and the size of the catalogue is not the only thing wrong with
it. A larger hand-curated list of AI/ML roles is still a list of AI/ML roles.

## 4a. What the AI assistant can be wrong about

The AI layer is optional, but it is not infallible, and the failure modes are
different from the engine's. The engine is wrong only when its inputs are
wrong, and it is wrong the same way every time. A model is wrong in ways that
depend on the question, and it is wrong in a fluent, confident register.

**The safeguards are structural, not advisory.** A prompt that says "do not
invent anything" is advice. The things that actually hold are:

- the model is never asked for a number the engine owns;
- a skill it names that is not in the verified gap set is dropped;
- a learning resource it names that the registry does not hold resolves to
  nothing, and it never sees a URL at all;
- a CV claim with no source in the user's own record is returned as a
  question, not as a draft sentence.

Those are enforced in code and asserted in `tests/test_ai_trust_boundary.py`.
What they do **not** do is make the prose true. A well-phrased suggestion can
still misdescribe a project, and a mentor answer can still be less good than a
person's own understanding of their career. The suggestions are a draft to
argue with, which is why the interface labels them that way and why the CV
advisor asks for what it is missing instead of filling the gap.

**The model has no knowledge of the labour market either.** The mentor is
grounded in your record and in the application's knowledge base, and both are
as limited as section 1 and section 4 describe. It will not tell you which
roles are hiring, because nothing here knows.

**The interview score is a practice score.** It measures how your answer
performed against five named dimensions, and the dimensions are shown next to
it so you can disagree with them. It is not a prediction of hiring, and the
interface says so every time the number appears.

**The learning resources are a curated list, not a search engine.** 211
verified official documents covering 247 of the 250 taxonomy skills. A skill
without one gets the learning task and no link, which is the honest outcome
rather than a plausible-looking one.

**The Bangla is a translation, not a localisation.** The English technical
terms are kept in English on purpose — a reader who needs to look up
`FastAPI` cannot look it up in Bangla. What is translated is the explanation
around them, and the quality of that translation is the model's, not a
human translator's.

**Nothing is measured.** There is no evaluation of the AI layer's output
quality, because there is no labelled set of good career advice to measure it
against. The tests assert that the layer is *well-behaved* — grounded,
bounded, honest about what it does not know. They do not assert that it is
*good*. That is a real gap and it is stated here rather than implied away.

## 5. How it runs

- **Single-region deployment.** One Render region, one database. No read
  replicas, no multi-region failover.
- **The free tier is the free tier.** Render's free web service is 512 MB of
  RAM and 0.1 of a CPU. The engine's steady resident set is about 220 MB with
  one worker, so the deployment runs **one** worker on that plan; the Docker
  image's two-worker default needs roughly 440 MB and would be killed by the
  memory limit. The upload volume is on the container filesystem, and the free
  tier has no persistent disk, so **an uploaded CV does not survive a
  redeploy**. The extracted text — which is what every downstream feature
  reads — is in the database and does survive.
- **The demonstration database has a shelf life.** A free Render Postgres
  instance expires 30 days after it is created, and a free Neon project
  suspends itself after inactivity. Either way, the database is a
  demonstration, not an archive, and the procedure for replacing it is in
  [`deployment.md`](deployment.md). The seed scripts are idempotent, so
  rebuilding the knowledge base is one command.
- **The rate limit is deployment-wide, not global.** The counters live in the
  database rather than in a process's memory, so every worker and every replica
  counts the same events — a two-worker deployment used to allow twice the
  configured number of attempts. The limit is still per database: two
  deployments with two databases have two limits.
- **The rate limit counts on the peer address, unless a proxy is trusted.**
  `X-Forwarded-For` is client-supplied, so a server that believed it
  unconditionally would let a caller rotate the header and get an unlimited
  number of password attempts. The API believes the header only from an
  address listed in `TRUSTED_PROXY_CIDRS`, and walks the chain from the
  right so that a caller's own forged prefix is discarded. A deployment that
  leaves the variable unset counts every request from the proxy as one
  address, which is the safe direction but a limit everyone shares.
- **Deleting an account deletes the uploaded files, not just the rows.** The
  database cascade removes the `resume_upload` rows; the files themselves are
  unlinked explicitly, because a row is not a file and a CV left on disk holds
  a name, contact details and employment history in plain text.
- **Email is exercised against a real mail server, and not against a commercial
  one.** The SMTP transport is driven end to end against a live server in the
  test suite — the socket, the `EHLO`, the `STARTTLS` negotiation, the
  authentication and the body — and the certificate is verified against a trust
  store the application chooses. What is still not established is that a
  commercial provider accepts what this sends. A deployed instance also
  cannot send mail: the free tier blocks outbound SMTP on ports 25, 465 and
  587, so the transport there is the file transport, which writes the message
  to the container's filesystem rather than sending it.
- **Accessibility is machine-verified, and not audited by a person.** `axe-core`
  runs over every route in both colour schemes; a keyboard walkthrough checks
  the tab order, the focus indicator, the focus trap and the focus return; a
  reflow check measures the layout at 320 CSS pixels and at 200% zoom; and a
  browser suite walks the whole journey. The screen-reader pass has not been
  done and no WCAG conformance statement is made, because
  [`accessibility-audit.md`](accessibility-audit.md) says exactly what was and
  was not checked.
- **The LLM learning path is implemented but disabled** (`LLM_ENABLED=false`).
  It is reachable through one endpoint and degrades to deterministic local steps
  with no key present. It has never been exercised against a live provider.
- **No mobile application.** The Next.js app is responsive and works on a phone
  viewport, but it is not a native app.
- **No social or networking features**, no job board, no employer side, no
  application tracking. These are excluded by proposal §18.9, and the compliance
  matrix verifies their absence.
- **No localisation.** English only, throughout.

## 6. What would raise confidence

In rough order of value per unit of effort:

1. **Independent labels.** Have career practitioners or final-year students rank
   candidate profiles and compare with the engine. This is the single largest
   gap and needs no new code.
2. **The signals, measured on real profiles.** The matched-pair study measures
   the mechanism; it says nothing about whether the signals help a real
   candidate, because the pairs are synthetic and purpose-built. Real profiles
   carrying years of experience, a level, recency and depth would answer it.
3. **Real usage data.** Whether users act on the shortlist is the only outcome
   metric that would settle question 1 empirically, and nobody has used the
   product at scale. The outcome actions in the feedback loop are the beginning
   of that, and they are self-reported.
4. **A proficiency rubric that is actually followed.** A study showing that
   users rate themselves against the rubric, rather than against their peers,
   would change how much the proficiency signal can be trusted.
