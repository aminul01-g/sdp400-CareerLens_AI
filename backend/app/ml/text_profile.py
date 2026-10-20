"""Building the profile text that feeds TF-IDF."""

from __future__ import annotations

from app.ml.types import ProfileSnapshot

#: Separator between fields. A single space keeps the text a normal sentence-like
#: bag of words; newlines would survive tokenisation as noise.
_FIELD_SEPARATOR = " "


def _weighted_skill_phrase(snapshot: ProfileSnapshot) -> str:
    """Repeat skill names in proportion to proficiency.

    **This is a deliberate design choice, and the alternative is worse.** If skill
    names appear exactly once, a 5/5 in TensorFlow and a 1/1 in TensorFlow produce
    *identical* TF-IDF vectors — the vectorizer cannot see strength, only
    presence. But a job-matching signal is precisely about strength, so the
    stronger skill is repeated more often. ``sublinear_tf=True`` in the
    vectorizer damps the resulting term frequency so the repeat cannot dominate.
    """
    pieces: list[str] = []
    for skill in sorted(snapshot.skills, key=lambda s: s.name):
        name = skill.name or skill.slug
        if not name:
            continue
        # 1..5 proficiency -> 1..5 mentions. A proficiency-1 skill still appears
        # once, so presence is never lost; only emphasis varies.
        pieces.extend([name] * max(1, min(5, skill.proficiency)))
    return _FIELD_SEPARATOR.join(pieces)


def build_profile_text(snapshot: ProfileSnapshot) -> str:
    """Concatenate everything the engine knows into one document.

    Order is fixed so the text is byte-identical for identical input, which is
    what the determinism test asserts.
    """
    parts: list[str] = []

    # 1. Narrative fields, once each.
    #
    # ``industry`` is here because it is topical: "fintech" and "e-commerce"
    # are words a role description also contains, so they carry real lexical
    # signal about which roles a profile belongs with.
    #
    # ``location`` is deliberately **not** here. A city name does not describe a
    # role, and adding it to the document would add a token that matches no
    # role description while diluting the vector for every user who filled the
    # field in — quietly lowering their text similarity. The field is read and
    # carried, but it is not scored against a market that does not exist.
    for value in (
        snapshot.headline,
        snapshot.career_goal,
        snapshot.bio,
        snapshot.preferred_role_family,
        snapshot.industry,
    ):
        if value and value.strip():
            parts.append(value.strip())

    # 2. Skills, weighted by proficiency.
    weighted_skills = _weighted_skill_phrase(snapshot)
    if weighted_skills:
        parts.append(weighted_skills)

    # 3. Projects: title, description, then the tech stack.
    for project in snapshot.projects:
        if project.title:
            parts.append(project.title)
        if project.description:
            parts.append(project.description)
        parts.extend(entry for entry in project.tech_stack if entry)

    # 4. Education.
    for record in snapshot.education:
        parts.extend(
            value for value in (record.degree, record.field_of_study, record.institution) if value
        )

    # 5. Certifications.
    for certification in snapshot.certifications:
        parts.append(certification.name)
        if certification.issuer:
            parts.append(certification.issuer)

    return _FIELD_SEPARATOR.join(part for part in parts if part).strip()


def with_profile_text(snapshot: ProfileSnapshot) -> ProfileSnapshot:
    """Return a copy of ``snapshot`` with ``profile_text`` populated.

    ``ProfileSnapshot`` is frozen, so this is the only way to attach the derived
    text — and doing it in one place keeps every caller consistent.
    """
    from dataclasses import replace

    return replace(snapshot, profile_text=build_profile_text(snapshot))
