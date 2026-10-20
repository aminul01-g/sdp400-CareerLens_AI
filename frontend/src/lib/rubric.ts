/**
 * The proficiency rubric, shared between the client and the documentation.
 *
 * `docs/proficiency-rubric.md` is the source of truth. This file is the
 * machine-readable copy of the level names and their descriptions, so the
 * "what does 4 mean?" question can be answered next to the control that asks
 * for it rather than only in a document the user has to go and find.
 *
 * The engine's own mapping — `(level - 1) / 4` — is the reason the levels are
 * described as equal fifths of independent capability. If the engine's mapping
 * changes, this file's wording has to change with it.
 */

export interface ProficiencyLevel {
  level: number;
  name: string;
  /** What a person at this level can do. */
  can: string;
  /** What they cannot do yet. */
  cannot: string;
  /** The factor the engine scores this level with. */
  factor: number;
}

export const PROFICIENCY_LEVELS: readonly ProficiencyLevel[] = [
  {
    level: 1,
    name: "Aware",
    can: "Recognise the technology and what it is for. Read documentation about it.",
    cannot: "Use it without a tutorial.",
    factor: 0,
  },
  {
    level: 2,
    name: "Assisted",
    can: "Do something useful with it when following a guide, with errors to look up.",
    cannot: "Work on it unsupervised.",
    factor: 0.25,
  },
  {
    level: 3,
    name: "Independent",
    can: "Build, debug and ship working things with it on your own.",
    cannot: "Design a system around it, or make the hard calls.",
    factor: 0.5,
  },
  {
    level: 4,
    name: "Production",
    can: "Use it in production, choose between its options, and review other people's work in it.",
    cannot: "Be the recognised expert others come to for it.",
    factor: 0.75,
  },
  {
    level: 5,
    name: "Expert",
    can: "Set direction for how it is used in your team, mentor others, and handle the problems that have no standard answer.",
    cannot: "—",
    factor: 1,
  },
] as const;

/** The description of one level, or null for a level outside the scale. */
export function proficiencyLevel(level: number): ProficiencyLevel | null {
  return PROFICIENCY_LEVELS.find((entry) => entry.level === level) ?? null;
}

/** A one-line summary of a level, for the inline hint under the slider. */
export function proficiencySummary(level: number): string {
  const entry = proficiencyLevel(level);
  if (!entry) return "";
  return `${entry.level} — ${entry.name}. ${entry.can}`;
}
