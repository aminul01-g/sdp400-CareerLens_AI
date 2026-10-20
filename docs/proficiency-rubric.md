# Proficiency Rubric

What a proficiency number means, written down.

`docs/limitations.md` used to say that proficiency was "self-reported and
coarse": an integer from 1 to 5, entered by the user, with no verification, and
with a linear factor that rested on nothing more than "it is the simplest thing
that is not absurd".

This document is the other half of the answer. It does not make the number
*verified* — nothing here can, and nothing in the system can. What it does is
make "4" mean the same thing to everyone who enters it, so that two profiles
with a 4 in the same skill are actually comparable.

The rubric is the reference for:

- the self-report form (**Skills** screen, proficiency slider),
- the mapping from a level to the factor the engine scores with,
- the "how do I know what to pick" question the interface has to answer anyway.

---

## The five levels

Each level is defined by **what you can do without help**, not by how long you
have used something. Time is not evidence: ten years of copying code is not
level 4.

| Level | Name | You can… | You cannot… |
| --- | --- | --- | --- |
| **1** | Aware | Recognise the technology and what it is for. Read documentation about it. | Use it without a tutorial. |
| **2** | Assisted | Do something useful with it when following a guide, with errors to look up. | Work on it unsupervised. |
| **3** | Independent | Build, debug and ship working things with it on your own. | Design a system around it, or make the hard calls. |
| **4** | Production | Use it in production, choose between its options, and review other people's work in it. | Be the recognised expert others come to for it. |
| **5** | Expert | Set direction for how it is used in your team, mentor others, and handle the problems that have no standard answer. | — |

### Why these five

The levels are the ones a job description can actually distinguish. "Familiar
with" is level 2, "strong" is level 3, "expert" is level 4 or 5. A CV that says
"strong Python developer" maps to level 3, not to "some Python" — and the
difference between those two is the difference between a role that lists Python
at weight 1.0 being a 0% match and a 75% match.

### Worked examples

The same skill, at five levels, written the way a CV would write it:

| Level | Python |
| --- | --- |
| 1 | "Heard of Python" |
| 2 | "Used Python in a university course project" |
| 3 | "Built and maintained a FastAPI service in Python for two years" |
| 4 | "Owned our Python data pipeline; chose and standardised on Poetry, uv and Ruff across three services" |
| 5 | "Set the direction of our Python platform; maintain the internal library three teams depend on" |

---

## How a level becomes a number

The engine maps a level onto `[0, 1]` with a **linear** factor:

```text
proficiency_factor = (level − 1) / 4
```

| Level | Factor | What it means in a score |
| --- | --- | --- |
| 1 | 0.00 | "I have heard of it" earns no credit against a role that requires working command of it. |
| 2 | 0.25 | A quarter of the requirement is met. |
| 3 | 0.50 | Half the requirement is met. |
| 4 | 0.75 | Three quarters. |
| 5 | 1.00 | The requirement is fully met. |

Two properties of this mapping are deliberate and worth stating:

1. **Level 1 scores exactly zero.** A skill you have only heard of should not
   earn partial credit against a role that needs you to use it. This is the
   single most consequential choice in the whole scoring function.
2. **A full set at level 5 scores exactly 1.0**, so a compatibility percentage
   stays interpretable on a 0–100 scale.

The linear shape is a *simplification*, and it is now a simplification of the
rubric above rather than of nothing at all: the five levels are defined as
equal fifths of increasing independent capability, and a linear map is the
honest rendering of that. It is still a linear map. A future version could
weight the levels non-linearly — level 3 to level 4 involves more than level 2
to level 3 does — but doing so would need evidence this project does not have,
and a curve fitted to 26 synthetic profiles would be worse than an honest
straight line.

---

## The signals that corroborate a level

A self-reported level is a claim. Two optional fields let the claim be
supported, and the engine reads both:

| Field | Effect on the score | If left blank |
| --- | --- | --- |
| **Years used** | The depth signal. A skill used for less than five years is discounted, down to a floor of 0.80 of its declared strength. | No adjustment. |
| **Last used** | The recency signal. A skill last used a year ago keeps full strength; one last used five years ago decays to a floor of 0.70. | No adjustment. |

Both are **optional and neutral when absent**. Not knowing when you last used
something is not evidence that you never used it, and the engine does not treat
it that way. A skill with neither field is scored on its declared proficiency
alone, exactly as it was before these signals existed.

The combined discount is floored at **0.70**: a skill that is both stale and
shallow keeps at least 70% of its declared strength. It is discounted, never
erased — you still have the skill.

---

## What this rubric does not solve

- **Nothing here verifies anything.** A level is still a self-report, and
  self-reports are biased upward: people rate themselves against peers rather
  than against a rubric. The rubric makes the claim *comparable*, not *true*.
- **It is not profession-specific.** A level 4 in Rust and a level 4 in Excel
  are defined by the same words but mean different amounts of work. The
  definitions are written to survive that, but they do not eliminate it.
- **It does not cover the "depth" question on its own.** How much you have
  written versus read is answered by the *years used* field, not by the level.

These are recorded as residual limitations in
[`limitations.md`](limitations.md#4-proficiency-is-self-reported-and-biased-upward).
