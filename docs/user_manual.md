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
- [8. Admin tools](#8-admin-tools)
- [9. Troubleshooting](#9-troubleshooting)
- [10. Privacy](#10-privacy)

---

## 1. Getting an account

Go to the site and choose **Register**. You need a name, an email address and a
password of at least 8 characters.

- The email must be a real, deliverable address. It has to be unique — if an
  account already exists with that address you will be told, and you should log in
  instead.
- The password is stored as a bcrypt hash. Nobody, including an administrator, can
  read it.
- You are signed in immediately after registering; there is no email confirmation
  step.

Already have an account? **Log in** with the same email and password.

To change your name, use your account page. To change your password you must
supply the current one.

**If you forget your password, there is no reset link.** This is a known
limitation, recorded in [`limitations.md`](limitations.md#8-operational-limits).

## 2. Your profile

One profile per account, at **Profile**.

| Field | Notes |
|---|---|
| Headline | One line. The single most useful field — it is weighted into your match. |
| Career goal | What you are aiming for. Free text; also weighted. |
| Bio | A paragraph about you. |
| Preferred role family | Optional. A preference, not a filter — it does not remove other families from your results. |

The dashboard shows a **profile completeness** figure. It is computed from your
actual records, not a stored number, so it moves as you add things.

## 3. Skills

This is what the matching engine actually reads, so it is worth the most effort.

**Adding a skill.** Go to **Skills**, search the taxonomy, pick one, and set a
proficiency:

| Level | Means |
|---|---|
| 1 | Awareness. You have read about it. |
| 2 | Basic familiarity. You can follow a tutorial. |
| 3 | Working knowledge. You could do this with reference material. |
| 4 | Strong. You could do this unsupervised. |
| 5 | Expert. You could teach it and design around it. |

The number is what the formula consumes: level 1 contributes 0, level 5
contributes 1.0. **Be honest.** A uniformly high list produces a shortlist that
looks confident and is wrong.

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
2. The text is extracted.
3. Skills are **proposed**, not applied.
4. **You review the list and choose what to accept.**

This last step matters. The extractor is a phrase matcher: it can find a skill
named in passing, or miss one written as an abbreviation. It also cannot read
layout, so a word in a sentence is treated the same as a word in a skills list.
**Read the proposals before accepting them.**

For each suggestion you set the proficiency yourself. Accepted skills are tagged
`cv_extracted` in the database so you can tell later where a skill came from.

Rejected suggestions are simply not added. Nothing is lost either way — you can
always add a skill by hand.

**If your CV is a scan or a photograph, the upload will be refused** with a
message saying so. There is no OCR. Type your skills in instead.

## 6. Getting recommendations

**Recommendations** in the menu. Press **Generate**.

The engine scores your profile against all 82 roles and shows a shortlist. The
first run also records the run, so you can look at it again later from
**Recommendation history** without regenerating.

**Reading a score.** Each result shows a percentage and, underneath, the two
components that produced it:

| Component | What it measures |
|---|---|
| Skill coverage | How much of the role's required skills you have, weighted by how much the role depends on each one, scaled by your stated proficiency. |
| Text similarity | How closely your headline, goal, bio and projects resemble the role's description. |

The combined score is `0.6 × coverage + 0.4 × text similarity`. The breakdown is
shown so you can check the arithmetic — it is meant to be verifiable, not
persuasive.

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

**The learning path** button turns the gap into a short study plan. It is optional
and **switched off in this deployment**, so the button either does nothing or is
absent. That is intentional — the core features work without it. When no provider
is configured, the plan falls back to deterministic local steps, so it never
fails and never blocks.

## 8. Admin tools

For accounts with the administrator role only. If you cannot see the admin section,
you do not have it.

| Page | What it does |
|---|---|
| Overview | Real counts: users, roles, skills, runs, most-required skills. |
| Job roles | Browse all 82 roles. Create, edit and delete them. Edit the weight of each required skill. |
| Users | List accounts. Change a user's role. |
| Taxonomy | Browse the 151 skills. Add, edit and remove them. |
| Evaluation | The published evaluation numbers, read from the committed report. |
| Feedback | Everything users have submitted. |

**Changing a role's weights changes everyone's scores immediately.** A weight must
be greater than 0 and at most 1, and a role needs at least one required skill to
be saved at all. The seeded roles carry 8 to 18, which is where the knowledge base
settled, but that is a property of the data rather than a rule the API enforces —
you can save a role with a single requirement, and it will rank almost nobody.
Delete a role and existing recommendation history keeps its recorded scores, but
the role can no longer be generated.

**Evaluation** is read-only on purpose. It shows the report committed to the
repository, so the chart can never disagree with the document.

## 9. Troubleshooting

**"The page won't load" / "Failed to fetch"**
The API is unreachable or CORS is blocking you. If you are self-hosting, check
that the API is up and that its `ALLOWED_ORIGINS` includes the exact origin you
are browsing from, including scheme and port — `http://localhost:3000` and
`https://localhost:3000` are different origins.

**"Your session has expired"**
Sessions last 24 hours by default. Log in again. Your data is not affected.

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

**"This PDF appears to be a scan"**
No text layer. There is no OCR. Add your skills by hand.

**"Unsupported document type"**
Only PDF and DOCX. Not DOC, not RTF, not an image.

**Recommendations are empty**
Your profile has no skills, so coverage is 0 everywhere. Add skills first.

**My upload detected skills I do not have**
Expected. The extractor matches text, not meaning. Decline them. This is the
confirmation step doing its job.

## 10. Privacy

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
