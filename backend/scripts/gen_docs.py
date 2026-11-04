"""Regenerate DATABASE_SCHEMA.md tables and the endpoint list in API_DOCUMENTATION.md from code.

Usage (from backend/): .venv/Scripts/python scripts/gen_docs.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "sqlite://")

import app.models  # noqa: E402,F401
from app.db.session import Base  # noqa: E402
from app.main import app  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BEGIN, END = "<!-- BEGIN GENERATED -->", "<!-- END GENERATED -->"


def schema_md() -> str:
    out = []
    for t in sorted(Base.metadata.sorted_tables, key=lambda t: t.name):
        out.append(f"### `{t.name}`\n")
        out.append("| Column | Type | Null | Key / constraint |\n|---|---|---|---|")
        for c in t.columns:
            keys = []
            if c.primary_key:
                keys.append("PK")
            for fk in c.foreign_keys:
                keys.append(f"FK → `{fk.target_fullname}` ({fk.ondelete or 'NO ACTION'})")
            if c.unique:
                keys.append("unique")
            if c.index:
                keys.append("indexed")
            typ = str(c.type).replace("|", "/")
            out.append(f"| `{c.name}` | {typ} | {'yes' if c.nullable else 'no'} | {', '.join(keys)} |")
        uniques = [u for u in t.constraints if u.__class__.__name__ == "UniqueConstraint" and len(u.columns) > 1]
        for u in uniques:
            out.append(f"\nUnique: ({', '.join(c.name for c in u.columns)})")
        out.append("")
    return "\n".join(out)


def endpoints_md() -> str:
    spec = app.openapi()
    rows = ["| Method | Path | Summary | Token |", "|---|---|---|---|"]
    for path, ops in sorted(spec["paths"].items()):
        for method, op in ops.items():
            auth = "admin or moderator role" if "/admin" in path else ("accepted (see route)" if op.get("security") else "not used")
            rows.append(f"| {method.upper()} | `{path}` | {op.get('summary', '')} | {auth} |")
    return "\n".join(rows)


def replace(path: str, generated: str) -> None:
    s = open(path, encoding="utf-8").read()
    a, b = s.index(BEGIN) + len(BEGIN), s.index(END)
    open(path, "w", encoding="utf-8").write(s[:a] + "\n\n" + generated + "\n\n" + s[b:])


if __name__ == "__main__":
    replace(os.path.join(ROOT, "DATABASE_SCHEMA.md"), schema_md())
    replace(os.path.join(ROOT, "API_DOCUMENTATION.md"), endpoints_md())
    print("docs regenerated")
