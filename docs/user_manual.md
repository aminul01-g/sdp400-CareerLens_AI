# User Manual

Everything you can do in CareerLens AI, from registration to the skill-gap report,
plus what to do when something goes wrong.

- [1. Getting an account](#1-getting-an-account)
- [2. Your profile](#2-your-profile)
- [3. Skills](#3-skills)
- [4. Projects, education, certifications](#4-projects-education-certifications)
- [5. Uploading a CV](#5-uploading-a-cv)
- [6. Getting recommendations](#6-getting-recommendations)
- [7. Reading your skill gap](#7-reading-your-skill-gap)
- [8. The AI assistant](#8-the-ai-assistant)
- [9. Admin tools](#9-admin-tools)
- [10. Troubleshooting](#10-troubleshooting)
- [11. Privacy](#11-privacy)

---

## 1. Getting an account

Go to the site and choose **Register**. You need a name, an email address and a
password of at least 8 characters.

- The email must be a real, deliverable address. It has to be unique — if an
  account already exists with that address you will be told, and you should log in
  instead.
- The password is stored as a bcrypt hash. Nobody, including an administrator, can
  read it.
- You are signed in immediately after registering. A confirmation email is sent
  as well, but confirming your address is optional — it is not required to use
  the product.

Already have an account? **Log in** with the same email and password.

To change your name, use your account page. To change your password you must
supply the current one. Changing it signs out your other sessions immediately.

**If you forget your password**, use **Forgot your password?** on the sign-in
page. We send a link to your address; it can be used once and expires
shortly. The confirmation you get is the same whether or not the address has an
account, so the page cannot be used to find out who is registered.

**If you change your password or reset it, every session you have open is
signed out.** You will be asked to sign in again, and the sign-in page will say
why.

## 2. Your profile

One profile per account, at **Profile**.

| Field | Notes |
|---|---|
| Headline | One line. The single most useful field — it is weighted into your match. |
| Career goal | What you are aiming for. Free text; also weighted. |
| Bio | A paragraph about you. |
| Location | Optional. Recorded and shown, but **not** scored — there is no labour-market data behind it. |
| Industry | Optional. The sector you work in. It is part of the text your profile is matched on. |
| Current level | Optional. Entry, Junior, Mid, Senior, Lead or Principal. Roles at a different level are still shown, but scored lower. Leaving it blank costs you nothing. |
| Years of experience | Optional. Used to work out your level if you have not set one. |
| Preferred role family | Optional. A preference, not a filter — it does not remove other families from your results. |

Below the fields is your **work history**: the roles you have held, and the
dates. It is what the engine uses to work out your level when you have not
declared one, and it can be read out of an uploaded CV for you to confirm.
Overlapping roles count once — two jobs at the same time is not two years of
experience.

The dashboard shows a **profile completeness** figure. It is computed from your
actual records, not a stored number, so it moves as you add things.

## 3. Skills

This is what the matching engine actually reads, so it is worth the most effort.

**Adding a skill.** Go to **Skills**, search the taxonomy, pick one, and set a
proficiency:

| Level | Means |
|---|---|
| 1 | Aware. You recognise it and know what it is for. You cannot use it without a tutorial. |
| 2 | Assisted. You can get something useful out of it by following a guide. You cannot work on it unsupervised. |
| 3 | Independent. You can build, debug and ship with it on your own. You cannot design a system around it. |
| 4 | Production. You use it in production, choose between its options, and review other people's work in it. |
| 5 | Expert. You set the direction for how it is used in your team and mentor others. |

The number is what the formula consumes: level 1 contributes 0, level 5
contributes 1.0. The full rubric is in
[`proficiency-rubric.md`](proficiency-rubric.md), and the levels are shown next
to the slider on the Skills screen. **Be honest.** A uniformly high list
produces a shortlist that looks confident and is wrong.

**Years used and last used.** Each skill has two optional fields. "Years used"
is how long you have actually worked with it, and "last used" is when you last
did. The engine discounts a skill you have not touched in a while, and one you
have only just started, so it can tell a decade of practice from a fortnight.
Both are optional and **leaving them blank costs you nothing** — a skill with
neither is scored on its proficiency alone.

**Editing and removing.** Change the proficiency or delete any skill at any time.
Removing a skill changes your scores immediately.

**What the number means for you.** Each role's requirements carry a weight. A skill
at weight 0.95 in a critical role counts about three times as much as one at 0.3.
That is why the gap report tells you to fix the 0.95 before the 0.4.

## 4. Projects, education, certifications

All three are full CRUD — add, edit, delete.

- **Projects** take a title, a description, and a tech stack. The tech stack is
  matched against the taxonomy, so a project is worth more than an equivalent
  sentence of prose in your bio. Write the description anyway: it feeds the text
  similarity component.
- **Education** records are per-entry, so several qualifications do not overwrite
  each other.
- **Certifications** record a name and an issuer. Dates are optional.

**Deleting is permanent** and always asks for confirmation. Your profile is the
only copy of this information.

## 5. Uploading a CV

**Profile → Resume**, or the upload area on the CV page. PDF and DOCX, up to the
size limit shown.

What happens:

1. The file is checked — size, extension, and that it is really the format it
   claims to be.
2. The text is extracted and split into sections.
3. Skills are **proposed**, not applied.
4. **You review the list and choose what to accept.**

This last step matters. The extractor is a phrase matcher: it can find a skill
named in passing, or miss one written as an abbreviation. **Read the proposals
before accepting them.**

It does now know the sections, so each proposal is labelled:

- **Declared** — found under a heading like *Skills*. This is a claim about
  you.
- **Mentioned in projects** — found inside a project or role description. It
  may be your work or your employer's; treat it with more caution.

If your CV has an **Experience** section, the roles in it are read as well and
proposed as work-history entries, with their dates. Those are proposals too:
confirm them on your **Profile** page and they will count towards your
experience.

The quantified claims in your CV are read as well. A sentence with a number in
it — "reduced query time by 80%", "saved $2M a month", "handled 12,000
requests" — is listed under **We read N quantified claims from your CV**, and
each one is marked as reading as *your* work or as *the team's*, according to
whether the sentence says "I" or "we".

Those claims do not change your score. They are there so you can see what the
document says about you, and edit the CV if it says it badly.

For each suggestion you set the proficiency yourself. Accepted skills are tagged
`cv_extracted` in the database so you can tell later where a skill came from.

Rejected suggestions are simply not added. Nothing is lost either way — you can
always add a skill by hand.

**If your CV is a scan or a photograph, the upload will be refused** with a
message saying so. There is no OCR. Type your skills in instead.

## 6. Getting recommendations

**Recommendations** in the menu. Press **Generate**.

The engine scores your profile against all 100 roles and shows a shortlist. The
first run also records the run, so you can look at it again later from
**Recommendation history** without regenerating.

**Reading a score.** Each result shows a percentage and, underneath, the two
components that produced it:

| Component | What it measures |
|---|---|
| Skill coverage | How much of the role's required skills you have, weighted by how much the role depends on each one, scaled by your stated proficiency, how recently you used it and how long you have used it. |
| Text similarity | How closely your headline, goal, bio, industry and projects resemble the role's description. |

The combined score is `0.6 × coverage + 0.4 × text similarity`. The breakdown is
shown so you can check the arithmetic — it is meant to be verifiable, not
persuasive. It also shows the adjustments, when they are not zero:

- **Recency and depth** — shown when a skill you have is discounted because you
  have not used it lately, or have only just started it.
- **Level fit** — shown when your declared level and the role's are not the
  same. A role two bands away is scored lower, but it is still on the list.

**Saying what you think.** Each result has **Save** and **Not for me**, and a
**How did it go?** row with **I applied**, **Got an interview** and **Got an
offer**. Marking a role tells the system what you thought of it, and the
aggregate of everybody's answers moves future rankings by a small amount.

An outcome counts for more than an opinion: a role somebody got an interview
for is better evidence of a good match than a role somebody merely saved. The
adjustment is bounded at ten per cent, and it only applies once a role has
enough answers to be worth acting on. It reorders the list; it never removes
anything from it.

The outcome buttons are for reporting what happened to *you*, after you left
the shortlist. Nothing is sent anywhere: the application cannot apply to a job
on your behalf, and it does not try.

**What a percentage is not.** It is not a probability of getting the job, and not
a ranking against other people. It is a similarity measure between your declared
profile and a role definition. Read [`limitations.md`](limitations.md) before
drawing conclusions from it.

**If scores look low across the board**, it is almost always because you have not
added your skills yet. Coverage dominates the score, and a nearly empty profile
scores nearly zero on every role. That is correct behaviour, not a bug.

## 7. Reading your skill gap

Open any result to see what is missing for that specific role.

Missing skills are listed **in order of how much they matter** to that role, each
with a tier:

| Tier | Meaning |
|---|---|
| Critical | Required by the role. Start here. |
| Important | Strongly expected. Learn it after the critical items. |
| Desirable | Useful but not blocking. Learn once the essentials are solid. |

The ordering is strictly by weight, so the first item is the highest-value thing
you can learn next. Work down the list in order; the payoff falls off sharply
after the critical tier.

**The learning path** button turns the gap into a short study plan. It is
optional: when no provider is configured, the plan falls back to deterministic
local steps, so it never fails and never blocks.

For a full plan — weeks, tasks, a portfolio project and something to work
through — use **Learning roadmap** in the AI assistant (section 8).

## 8. The AI assistant

Five screens, reached from **AI Assistant** in the header or from the cards on
your dashboard. They share a sub-navigation, so you can move between them
without going back to the header.

They are **optional**. On a deployment with no model provider configured, each
one says so and links you back to the features that do work. Nothing you have
already entered is affected.

### The career mentor (`/mentor`)

Ask a question in your own words. The answer is built from your confirmed
skills, your projects, your education, your latest recommendation run and your
skill-gap report — and the panel under the answer says which of those it used.

If something your question needs is not in your record, the assistant says so
and asks for it. It will not invent an employer, a credential, a metric or a
salary figure, because the application holds no salary data at all.

Suggested questions are offered as buttons, and the first one is about *your*
top match from your latest run.

**The conversation is short-lived.** Only the last few turns are sent to the
provider, so a long conversation does not grow the request, and your transcript
is not stored by the application.

### Learning roadmaps (`/roadmaps`)

Pick a role and a length — four or six weeks — and the application turns the
role's **verified** skill gaps into a plan:

- the skills the plan targets are the ones the engine reported as missing, in
  the order it weights them;
- every task has activities, a deliverable and **completion criteria you can
  check**;
- each task shows its estimated hours, for a student with a part-time schedule;
- learning resources are **verified official documentation**, linked from a
  curated list;
- the plan ends in a **portfolio project** with a problem statement,
  technologies, milestones, expected outputs and how it would be judged.

Mark tasks complete, write notes against them, and paste a link to what you
built. Your progress is saved next to the plan, and the plan itself never
changes underneath you — regenerating makes a new one.

### Job analysis (`/job-analysis`)

Paste a job description, or pick a role from the knowledge base to compare it
against. You get the requirements split three ways, and the difference matters:

| | Meaning |
|---|---|
| **On your profile** | You have it, with the proficiency you declared |
| **Genuine gap** | The role verifiably needs it and you do not have it |
| **Not on your profile** | The description asks for it, and your record does not say either way |

The third one is not "you do not have this". It means nobody wrote it down. If
you have used it, add it to your skills and the next analysis will say so.

The coverage figure is measured against the skills extracted from the
description you pasted. When you also select a role from the knowledge base,
the engine's own score for that role is shown separately and labelled.

### CV advice (`/resume/advice`)

Choose one of your uploaded CVs and the assistant suggests how to present it
more clearly. It works from the document and your stored records, and it never
adds something you did not do.

- the suggestions are a **separate list** — your CV is not changed;
- where the CV is missing something, you are **asked for it** rather than
  having a sentence written for you;
- a draft professional summary, bullet points and an optional cover letter use
  only what is already in your record.

Read every suggested line against the truth of your own record before you use
it. The tool helps you describe what you did; it does not decide what you
should claim.

### Mock interview (`/interview`)

Choose a role and answer its questions in your own words. The questions are
drawn from the role's requirements and from your own experience, so they are
answerable rather than generic, and each one can be followed by a follow-up
based on what you actually said.

Your answer is scored against five dimensions — relevance, correctness,
completeness, reasoning and clarity — and the dimensions are shown next to the
score, each with the note explaining it. The score is a **practice score**, not
a prediction of hiring; the interface says so every time it appears.

Every session is saved with its questions, your answers and the feedback, so
you can read it again later.

### English or Bangla

Every generated explanation can be in **English** or **Bangla**. The toggle is
at the top of every AI screen, and the choice is saved to your profile.

Technical terms stay in English on purpose: if you need to look up `FastAPI` or
`pandas`, you need it spelled the way the documentation spells it. What is
translated is the explanation around them.

The language changes the *words*, never the *data*. Skill names, role titles
and every score stay exactly as the engine produced them.

## 9. Admin tools

For accounts with the administrator role only. If you cannot see the admin section,
you do not have it.

| Page | What it does |
|---|---|
| Overview | Real counts: users, roles, skills, runs, most-required skills. |
| Job roles | Browse all 100 roles. Create, edit and delete them. Edit the weight of each required skill, the role's level and the experience it expects. |
| Users | List accounts. Change a user's role. |
| Taxonomy | Browse the 250 skills. Add, edit and remove them. |
| Evaluation | The published evaluation numbers, read from the committed report. |
| Feedback | Everything users have submitted. |
| Audit log | Every administrative change and every sign-in, with who did it, when, and from where. Filter it by action. |

**Changing a role's weights changes everyone's scores immediately.** A weight must
be greater than 0 and at most 1, and a role needs at least one required skill to
be saved at all. The seeded roles carry 8 to 18, which is where the knowledge base
settled, but that is a property of the data rather than a rule the API enforces —
you can save a role with a single requirement, and it will rank almost nobody.
Delete a role and existing recommendation history keeps its recorded scores, but
the role can no longer be generated.

**Evaluation** is read-only on purpose. It shows the report committed to the
repository, so the chart can never disagree with the document.

**The audit log** records every change an administrator makes and every
sign-in, including the failed ones. It is written in the same transaction as
the change it describes, so it cannot disagree with the data. The record
outlives the account: deleting a user does not delete what that user did.
The client address is best-effort — behind a proxy it is the first entry of
`X-Forwarded-For`, which the proxy sets, not the client.

## 10. Troubleshooting

**"The page won't load" / "Failed to fetch"**
The API is unreachable or CORS is blocking you. If you are self-hosting, check
that the API is up and that its `ALLOWED_ORIGINS` includes the exact origin you
are browsing from, including scheme and port — `http://localhost:3000` and
`https://localhost:3000` are different origins.

**"Your session has expired"**
Sessions last 24 hours by default. Log in again. Your data is not affected.

**"Your password has changed since this session started"**
Your password was changed or reset, so the sessions that were open at the time
were signed out. This is deliberate. Sign in again with your current password.

**"Too many requests"**
You have sent more requests than the limit allows — ten sign-in attempts a
minute, for instance. The response says how long to wait in the `Retry-After`
header. Wait, and try again. If you are scripting against the API, slow down.

**"You do not have permission to perform this action"**
Either the account lacks the admin role, or the resource belongs to another user.
The second case returns this same message by design — confirming that a record
exists would leak information.

**"Email already registered"**
That address is in use. Log in instead.

**"The evaluation report has not been generated yet"**
Only an admin sees this, and it means the report file is missing from the
deployment. See [`deployment.md`](deployment.md).

**"The uploaded file is missing from storage" / upload fails with a server error**
The upload directory is not writable by the process. On the container this means
the image is wrong; locally it means the `uploads/` directory is missing or
permissions are wrong. See [`deployment.md`](deployment.md#10-local-docker-fallback).

**"That link is not valid, or has already been used"**
A verification or password-reset link can be used once and expires. Request a
new one and open it straight away — some mail clients rewrite links, and
clicking an old message can break the token.

**"This PDF appears to be a scan"**
No text layer. There is no OCR. Add your skills by hand.

**"Unsupported document type"**
Only PDF and DOCX. Not DOC, not RTF, not an image.

**Recommendations are empty**
Your profile has no skills, so coverage is 0 everywhere. Add skills first.

**"The AI assistant is not enabled on this deployment"**
The AI layer needs a model provider, and this deployment has no key configured.
Everything else in CareerLens — CV analysis, career matching, the skill-gap
report — works without it. An administrator can turn it on by setting
`GROQ_API_KEY` in the deployment's environment; there is nothing else to do.

**"The AI service is temporarily unavailable"**
The model provider could not be reached, or answered with something the
application could not read. This is a provider-side problem and it is usually
brief. Your saved plans, interviews and CVs are unaffected — try again in a
moment.

**"The AI service returned an answer this application could not read"**
The provider's answer did not match the shape the application asked for. It
retries once and then refuses rather than storing something malformed. Please
try again; if it repeats, it is worth reporting, because it points at a
provider behaviour change.

**A roadmap came back with fewer tasks than you expected**
A task that names a skill the application has not recorded as missing is
removed rather than shown, and a learning link the application cannot verify
is dropped. A plan that contains a skill you do not have would send you down
the wrong path.

**The mentor said it does not have something**
That is it being honest. Your record does not contain the fact the question
needed — an experience level, a salary, a job description. Add it, or ask a
different question.

**My upload detected skills I do not have**
Expected. The extractor matches text, not meaning. Decline them. This is the
confirmation step doing its job.

## 11. Privacy

What the system stores about you: name, email, a bcrypt password hash, your
profile, your skills and their proficiencies, your projects, education and
certifications, any CV you uploaded **and its extracted text**, and your
recommendation runs.

- **Your CV is stored as a file** with its extracted text kept alongside it. It is
  served only to you, and you can delete it from the CV page.
- **Deletion.** Deleting your account cascades: profile, skills, projects,
  education, certifications, CV uploads and recommendation runs all go with it.
- **Administrators cannot see your password.** It is hashed, and the API never
  returns it — there is a test that asserts the string `password` does not appear
  in any response.
- **Other users cannot see your profile.** Every user-scoped query filters by
  owner, and the tests check each entity for cross-user access.
- **The learning path, if ever enabled, sends only skill names and the role title**
  to a third-party provider. Not your name, email, bio or CV. There is a test
  that asserts the prompt contains no such field.
