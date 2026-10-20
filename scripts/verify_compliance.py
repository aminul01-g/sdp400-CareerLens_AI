#!/usr/bin/env python3
"""Repository-wide compliance checks that are easier to automate than to read.

Each check prints PASS or FAIL and the script exits non-zero if anything fails, so
it can be wired into CI or run as a single pre-submission gate.

Run:  python scripts/verify_compliance.py
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_SRC = ROOT / "frontend" / "src"
FRONTEND_APP = ROOT / "frontend" / "app"
BACKEND_APP = ROOT / "backend" / "app"

FAILURES: list[str] = []
PASSES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    (PASSES if ok else FAILURES).append(f"{name}{f' — {detail}' if detail else ''}")
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{f' — {detail}' if detail else ''}")


def code_lines(path: Path) -> list[tuple[int, str]]:
    """Source lines with comments and string literals removed.

    Several checks look for a *token* in application code, and several
    docstrings legitimately mention that token while explaining what was removed.
    A naive grep cannot tell the difference, and a check that fires on its own
    documentation is a check people learn to ignore.
    """
    text = path.read_text(errors="ignore")
    if path.suffix == ".py":
        # A Python docstring is an expression, not a comment, so a `#`-only filter
        # leaves it in place — and several of these docstrings legitimately quote
        # the very literals this script is looking for, while explaining that they
        # were removed. Blank them out with the AST rather than by regex.
        docstring_lines: set[int] = set()
        try:
            tree = ast.parse(text)
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    body = getattr(node, "body", [])
                    if (
                        body
                        and isinstance(body[0], ast.Expr)
                        and isinstance(body[0].value, ast.Constant)
                        and isinstance(body[0].value.value, str)
                    ):
                        docstring_lines.update(
                            range(body[0].lineno, (body[0].end_lineno or body[0].lineno) + 1)
                        )
        except SyntaxError:  # pragma: no cover - malformed file
            pass
        out = []
        for lineno, line in enumerate(text.splitlines(), 1):
            if lineno in docstring_lines or line.strip().startswith("#"):
                continue
            out.append((lineno, line))
        return out
    # A hand-rolled stripper, deliberately: Python's `tokenize` cannot parse
    # TypeScript or JSX (it raises TokenError on `\u2014` inside a string and on
    # JSX braces), and silently falling back to "no filtering" made this script
    # report its own documentation as a violation.
    return list(enumerate(_strip_js_comments(text).splitlines(), 1))


def _strip_js_comments(text: str) -> str:
    """Blank out // and /* */ comments while respecting string literals.

    The output keeps the original line numbering so a finding can still be
    located. A one-character space replaces every comment character, which keeps
    column-independent line matching working.
    """
    out: list[str] = []
    i, n = 0, len(text)
    quote: str | None = None
    in_line_comment = False
    in_block_comment = False

    while i < n:
        char = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if in_line_comment:
            if char == "\n":
                in_line_comment = False
                out.append(char)
            else:
                out.append(" ")
            i += 1
            continue
        if in_block_comment:
            if char == "*" and nxt == "/":
                out.append("  ")
                i += 2
                in_block_comment = False
                continue
            out.append("\n" if char == "\n" else " ")
            i += 1
            continue
        if quote is None and char == "/" and nxt == "/":
            in_line_comment = True
            out.append("  ")
            i += 2
            continue
        if quote is None and char == "/" and nxt == "*":
            in_block_comment = True
            out.append("  ")
            i += 2
            continue
        if quote is not None:
            out.append(char)
            if char == "\\" and nxt:  # escape sequence
                out.append(nxt)
                i += 2
                continue
            if char == quote:
                quote = None
            i += 1
            continue
        if char in "\"'`":
            quote = char
        out.append(char)
        i += 1
    return "".join(out)


def scan(roots: list[Path], needle: str, flags: int = re.IGNORECASE) -> list[str]:
    hits: list[str] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.suffix not in {".ts", ".tsx", ".js", ".jsx", ".py", ".css", ".json"}:
                continue
            for lineno, line in code_lines(path):
                if re.search(needle, line, flags):
                    hits.append(f"{path.relative_to(ROOT)}:{lineno}")
    return hits


def main() -> int:  # noqa: C901 - a checklist is linear by nature
    print("CareerLens AI — compliance checks\n")

    print("Architecture")
    hits = scan([BACKEND_APP], r"\b(import flask|from flask)\b")
    check("no Flask import under backend/app", not hits, ", ".join(hits[:3]))

    hits = scan([FRONTEND_SRC, FRONTEND_APP], r"react-router-dom|from ['\"]vite|import\.meta\.env")
    check("no react-router / vite / import.meta.env in frontend code", not hits, ", ".join(hits[:3]))

    create_all = scan([BACKEND_APP], r"create_all")
    check("no create_all in application code (Alembic owns the schema)", not create_all)

    hits = scan([BACKEND_APP / "ml"], r"\b(import sqlalchemy|from sqlalchemy|import fastapi|from fastapi|import starlette|from starlette|import psycopg|from psycopg)", re.IGNORECASE)
    check("app/ml imports no ORM or web framework", not hits, ", ".join(hits[:3]))

    print("\nNo fabricated data in production flows")
    for label, pattern in [
        ("mockRecommendations", r"mockRecommendations"),
        ("mockStats", r"\bmockStats\b"),
        ("mockQuizData", r"mockQuizData"),
        ("'12,847' user count", r"12,847"),
        ("'94%' success rate", r"[\"']94%[\"']"),
        ("'500+' career paths", r"[\"']500\+[\"']"),
        ("'18 minutes' completion time", r"18 minutes"),
        ("invented salary bands", r"averageSalary"),
    ]:
        hits = scan([FRONTEND_SRC, FRONTEND_APP, BACKEND_APP], pattern)
        check(f"no {label}", not hits, ", ".join(hits[:3]))

    print("\nSecurity")
    hits = scan([BACKEND_APP], r"jwt_required\s*\(\s*optional")
    check("no optional auth on any endpoint", not hits)

    # Scoped deliberately: `src/components/ui/chart.tsx` is vendored shadcn/recharts
    # code that the migration plan requires preserving byte-identically, and it uses
    # dangerouslySetInnerHTML for the recharts tooltip container. Editing vendored
    # code to satisfy a linter would make the next `shadcn add` produce a diff, which
    # is the thing being avoided. Recorded in docs/report.md as a known finding.
    hits = [h for h in scan([FRONTEND_SRC, FRONTEND_APP], r"dangerouslySetInnerHTML")
            if "/components/ui/" not in h]
    check("no dangerouslySetInnerHTML outside the preserved shadcn kit", not hits, ", ".join(hits[:3]))

    hits = scan([FRONTEND_SRC, FRONTEND_APP], r"console\.log\(.*password|console\.log\(.*token", re.IGNORECASE)
    check("no credentials logged to the console", not hits)

    hits = scan([BACKEND_APP], r"print\s*\(.*password_hash")
    check("backend never prints a password hash", not hits)

    print("\nProduct branding")
    for label, pattern in [("Pathfinder", r"Pathfinder"), ("CareerGuide", r"CareerGuide")]:
        roots = [FRONTEND_SRC, FRONTEND_APP, BACKEND_APP, ROOT / "docs"]
        hits = scan(roots, pattern)
        check(f"no '{label}' in source or docs", not hits, ", ".join(hits[:3]))

    print("\nML layer purity")
    ml_dir = BACKEND_APP / "ml"
    offenders: list[str] = []
    for path in sorted(ml_dir.rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            module = None
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    if top in {"sqlalchemy", "fastapi", "starlette", "alembic", "psycopg"}:
                        offenders.append(f"{path.name}:{alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                top = node.module.split(".")[0]
                if top in {"sqlalchemy", "fastapi", "starlette", "alembic", "psycopg"}:
                    offenders.append(f"{path.name}:{node.module}")
                if node.module.startswith("app.") and not node.module.startswith("app.ml"):
                    offenders.append(f"{path.name}: reaches outside app.ml ({node.module})")
    check("app/ml is pure (AST-verified)", not offenders, "; ".join(offenders[:3]))

    print("\nKnowledge base")
    import json

    taxonomy_path = ROOT / "backend" / "data" / "skills_taxonomy.json"
    roles_path = ROOT / "backend" / "data" / "job_roles.json"
    if taxonomy_path.exists():
        taxonomy = json.loads(taxonomy_path.read_text())
        skills = taxonomy.get("skills", [])
        # The proposal asked for "around 150 skills". The catalogue has grown
        # past that as the knowledge base was widened, so the band is a floor
        # rather than a fixed count — what is being checked is that the
        # taxonomy is neither empty nor unbounded, and that everything in it
        # is consistent.
        check("taxonomy has at least 150 skills", len(skills) >= 150, f"{len(skills)} skills")
        check("taxonomy has at most 400 skills", len(skills) <= 400, f"{len(skills)} skills")
        slugs = {s["slug"] for s in skills}
        surfaces: dict[str, str] = {}
        collisions = []
        for skill in skills:
            for form in [skill["name"], skill["slug"], *skill.get("aliases", [])]:
                key = re.sub(r"[-_.\s]+", " ", form.strip().lower()).strip()
                if key in surfaces and surfaces[key] != skill["slug"]:
                    collisions.append(key)
                surfaces.setdefault(key, skill["slug"])
        check("no alias is claimed by two skills", not collisions, ", ".join(collisions[:3]))
        check("every skill has at least 2 aliases", all(len(s.get("aliases", [])) >= 2 for s in skills))
    else:
        check("taxonomy file exists", False, str(taxonomy_path))

    if roles_path.exists():
        roles = json.loads(roles_path.read_text()).get("roles", [])
        check("50-100 job roles", 50 <= len(roles) <= 100, f"{len(roles)} roles")
        bad_refs = [
            f"{r['title']}->{e['skill_slug']}"
            for r in roles
            for e in r["skills"]
            if taxonomy_path.exists() and e["skill_slug"] not in slugs
        ]
        check("every role skill exists in the taxonomy", not bad_refs, ", ".join(bad_refs[:3]))
        check(
            "every role has 8-18 required skills",
            all(8 <= len(r["skills"]) <= 18 for r in roles),
        )
        check(
            "every weight is within (0, 1]",
            all(0 < e["weight"] <= 1 for r in roles for e in r["skills"]),
        )
        check(
            "every role has a non-empty description (required for TF-IDF)",
            all(r.get("description", "").strip() for r in roles),
        )
        # The knowledge base is not only an AI/ML list. This is the check that
        # keeps it that way: the limitations document used to say that "there
        # is no teacher, no nurse, no accountant", and a catalogue that loses
        # its breadth quietly would make that true again.
        families = {r.get("family", "") for r in roles}
        non_technical = {
            "Teaching",
            "Healthcare",
            "Accounting & Finance",
            "Civil & Electrical Engineering",
            "Marketing",
            "Human Resources",
        }
        present = non_technical & families
        check(
            "the knowledge base includes the non-technical families",
            len(present) >= 4,
            f"present: {sorted(present)}",
        )
        check(
            "the knowledge base includes a teacher, a nurse and an accountant",
            {"secondary-school-teacher", "registered-nurse", "accountant"}
            <= {r.get("slug", "") for r in roles},
        )
    else:
        check("job roles file exists", False, str(roles_path))

    print("\nRepository hygiene")
    import subprocess

    def git_tracked() -> set[str]:
        """Files git actually tracks.

        "Committed" is a question for git, not the filesystem: a developer's working
        copy legitimately contains an untracked .env and an untracked legacy
        database, and failing the build on those would train everyone to ignore the
        check. What matters is whether either one was ever *staged*.
        """
        try:
            result = subprocess.run(
                ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, timeout=60
            )
        except (OSError, subprocess.SubprocessError):  # pragma: no cover
            return set()
        if result.returncode != 0:
            return set()
        return set(result.stdout.split())

    tracked = git_tracked()
    if tracked:
        # A template is not a secret and belongs in the repository; the file
        # itself is not. Anything named like a sample, example or template is
        # allowed, anywhere in the tree, rather than one hardcoded path.
        template_suffixes = (".example", ".sample", ".template", ".dist")
        tracked_env = [
            name
            for name in tracked
            if Path(name).name.startswith(".env")
            and not name.endswith(template_suffixes)
        ]
        check("no .env is tracked by git", not tracked_env, ", ".join(tracked_env[:3]))

        # A template earns that exemption by containing no real values. Placeholders
        # are fine; anything that looks like a populated secret is not, and shipping
        # one in a file named .example is the classic way a real key leaks.
        secretish = re.compile(
            r"(?i)\b(api[_-]?key|secret|password|passwd|token)\b\s*[=:]\s*[\"']?([^\s\"']+)"
        )
        offenders: list[str] = []
        for name in sorted(tracked):
            if not name.endswith(template_suffixes):
                continue
            try:
                body = Path(name).read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for lineno, line in enumerate(body.splitlines(), start=1):
                if line.lstrip().startswith("#"):
                    continue
                match = secretish.search(line)
                if not match:
                    continue
                value = match.group(2).strip()
                if not value or value.startswith(("<", "$", "{", "your", "change", "replace")):
                    continue
                offenders.append(f"{name}:{lineno}")
        check("no .env template ships a populated secret", not offenders, ", ".join(offenders[:3]))
        tracked_db = [name for name in tracked if name.endswith((".db", ".sqlite", ".sqlite3")) and not name.startswith("docs/archive/")]
        check("no SQLite database is tracked (except the documented archive)", not tracked_db, ", ".join(tracked_db[:3]))
        # The eight legacy Flask modules lived flat at backend/*.py. `backend/app/`,
        # `backend/tests/`, `backend/scripts/` and `backend/alembic/` are the new tree.
        new_prefixes = ("backend/app/", "backend/tests/", "backend/scripts/", "backend/alembic/")
        tracked_legacy = [
            name
            for name in tracked
            if name.startswith("backend/") and name.endswith(".py")
            and not name.startswith(new_prefixes)
        ]
        check("no legacy Flask module remains tracked", not tracked_legacy, ", ".join(tracked_legacy[:4]))
    else:
        print("  SKIP  git-tracked checks (not a git repository)")

    print(f"\n{len(PASSES)} passed, {len(FAILURES)} failed")
    if FAILURES:
        print("\nFailures:")
        for failure in FAILURES:
            print(f"  - {failure}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
