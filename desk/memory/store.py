"""
desk/memory/store.py — the Second Brain.

Two-track memory (the SSGM "reversible reconciliation" pattern, research round 1):
  * Append-only markdown lessons  = the immutable episodic log (source of truth).
    Files: desk/memory/lessons/<category>.md  — we ONLY ever append.
  * Rebuildable SQLite index       = the mutable, throwaway fast layer.
    File:  desk/memory/index.sqlite — derived; can be deleted and rebuilt from
    the markdown at any time. Periodic reconciliation bounds drift to O(N), not
    O(total-history) — a corrupted/poisoned index can never outlive a rebuild.

Retrieval is recency-weighted (exponential time-decay) so stale lessons fade after
a weather/market regime shift instead of misleading the agent (research round 5).

Every write passes the Write Gate (see write_gate.py): a proposed lesson that would
contradict a protected kernel fact is rejected before it can be stored. This is the
memory twin of the tool test-harness and blocks memory-poisoning.
"""

from __future__ import annotations
import sqlite3
import re
import math
import json
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, asdict

from desk.memory.write_gate import check_lesson, WriteGateError

MEM_DIR = Path(__file__).resolve().parent
LESSONS_DIR = MEM_DIR / "lessons"
INDEX_DB = MEM_DIR / "index.sqlite"
RETRIEVAL_HALFLIFE_DAYS = 30.0   # a lesson's weight halves every 30 days

LESSONS_DIR.mkdir(parents=True, exist_ok=True)

# A lesson block in markdown. Stable, greppable, append-only.
_LESSON_RE = re.compile(
    r"^## LESSON (?P<ts>\S+) \| category: (?P<category>[^\|]+?) \| bet: (?P<bet>.+)$",
    re.MULTILINE,
)


@dataclass
class Lesson:
    ts: str
    category: str
    bet: str
    outcome: str          # WON / LOST / VOID
    thesis: str
    root_cause: str
    rule: str             # the generalized, reusable rule (the "semantic gradient")
    tags: str             # comma-separated

    def to_markdown(self) -> str:
        return (
            f"## LESSON {self.ts} | category: {self.category} | bet: {self.bet}\n"
            f"- outcome: {self.outcome}\n"
            f"- thesis: {self.thesis}\n"
            f"- root_cause: {self.root_cause}\n"
            f"- rule: {self.rule}\n"
            f"- tags: {self.tags}\n\n"
        )

    def as_dict(self) -> dict:
        return asdict(self)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _category_file(category: str) -> Path:
    safe = re.sub(r"[^a-z0-9_-]", "-", category.lower())
    return LESSONS_DIR / f"{safe}.md"


# --------------------------------------------------------------------------- #
# WRITE — append-only, Write-Gate guarded.
# --------------------------------------------------------------------------- #
def append_lesson(lesson: Lesson) -> Path:
    """Validate against the Write Gate, then APPEND to the category log. Never edits."""
    check_lesson(lesson.as_dict())          # raises WriteGateError if it would poison memory
    path = _category_file(lesson.category)
    with path.open("a", encoding="utf-8") as f:
        f.write(lesson.to_markdown())
    return path


# --------------------------------------------------------------------------- #
# RECONCILE — rebuild the SQLite index from the markdown source of truth.
# --------------------------------------------------------------------------- #
def _parse_lessons_file(path: Path):
    text = path.read_text(encoding="utf-8")
    blocks = re.split(r"(?=^## LESSON )", text, flags=re.MULTILINE)
    for blk in blocks:
        m = _LESSON_RE.search(blk)
        if not m:
            continue
        fields = {"ts": m.group("ts"), "category": m.group("category").strip(),
                  "bet": m.group("bet").strip()}
        for key in ("outcome", "thesis", "root_cause", "rule", "tags"):
            fm = re.search(rf"^- {key}: (.*)$", blk, flags=re.MULTILINE)
            fields[key] = fm.group(1).strip() if fm else ""
        yield fields


def rebuild_index(db_path: Path = INDEX_DB) -> int:
    """Delete and rebuild the SQLite index from all markdown lessons. Returns count."""
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.execute("""
        CREATE TABLE lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT, category TEXT, bet TEXT, outcome TEXT,
            thesis TEXT, root_cause TEXT, rule TEXT, tags TEXT, source TEXT
        )""")
    con.execute("CREATE INDEX idx_cat ON lessons(category)")
    n = 0
    for path in sorted(LESSONS_DIR.glob("*.md")):
        for f in _parse_lessons_file(path):
            con.execute(
                "INSERT INTO lessons (ts,category,bet,outcome,thesis,root_cause,rule,tags,source)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (f["ts"], f["category"], f["bet"], f["outcome"], f["thesis"],
                 f["root_cause"], f["rule"], f["tags"], path.name),
            )
            n += 1
    con.commit()
    con.close()
    return n


# --------------------------------------------------------------------------- #
# READ — recency-weighted retrieval (Read Gate: stale lessons decay).
# --------------------------------------------------------------------------- #
def _age_days(ts: str) -> float:
    try:
        t = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return 9999.0
    return max(0.0, (datetime.now(timezone.utc) - t).total_seconds() / 86400.0)


def _decay_weight(ts: str) -> float:
    return 0.5 ** (_age_days(ts) / RETRIEVAL_HALFLIFE_DAYS)


def recall(category: str, limit: int = 5, db_path: Path = INDEX_DB) -> list[dict]:
    """
    Return the most relevant lessons for a category, recency-weighted so a regime
    shift lets old lessons fade. Auto-rebuilds the index if missing.
    """
    if not db_path.exists():
        rebuild_index(db_path)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT * FROM lessons WHERE category=? ORDER BY ts DESC", (category,)
    ).fetchall()
    con.close()
    scored = []
    for r in rows:
        d = dict(r)
        d["_weight"] = round(_decay_weight(d["ts"]), 4)
        scored.append(d)
    scored.sort(key=lambda d: d["_weight"], reverse=True)
    return scored[:limit]


def recall_asof(category: str, asof_ts: str, limit: int = 5,
                db_path: Path = INDEX_DB) -> list[dict]:
    """
    Embargo-aware recall (research round 5, oracle-fallacy guard). Returns only
    lessons recorded at or before `asof_ts`, so a backtest replaying a decision at
    time t cannot 'learn' from a bet that only resolved after t. Same recency
    weighting as recall().
    """
    if not db_path.exists():
        rebuild_index(db_path)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT * FROM lessons WHERE category=? AND ts<=? ORDER BY ts DESC",
        (category, asof_ts),
    ).fetchall()
    con.close()
    scored = []
    for r in rows:
        d = dict(r)
        d["_weight"] = round(_decay_weight(d["ts"]), 4)
        scored.append(d)
    scored.sort(key=lambda d: d["_weight"], reverse=True)
    return scored[:limit]


def category_counts(db_path: Path = INDEX_DB) -> dict:
    if not db_path.exists():
        rebuild_index(db_path)
    con = sqlite3.connect(db_path)
    rows = con.execute(
        "SELECT category, COUNT(*) FROM lessons GROUP BY category"
    ).fetchall()
    con.close()
    return {c: n for c, n in rows}


if __name__ == "__main__":
    n = rebuild_index()
    print(f"reconciled {n} lessons into {INDEX_DB.name}")
    print("category counts:", json.dumps(category_counts(), indent=2))
