"""
desk/memory/knowledge.py — the SEMANTIC tier of the Second Brain.

The Second Brain has two CoALA tiers (research round 1, memory taxonomy):

  * EPISODIC memory  (store.py)     — one append-only lesson per resolved bet. Raw,
                                       specific, noisy. "On 2026-06-12 the Dallas bet
                                       lost because GFS/ECMWF disagreed 4F."
  * SEMANTIC memory  (THIS module)  — distilled, generalized PRINCIPLES with a
                                       confidence that grows as evidence accumulates.
                                       "In Dallas, model disagreement predicts losses
                                       (seen 5x, confidence 0.71)."

`consolidate()` is the reflection step that turns many episodic lessons into a few
semantic principles. It runs each cycle and is idempotent: it groups lessons by
(category, primary-tag), and only writes a new principle note when the evidence count
or claim actually changed — so memory converges instead of growing without bound.

Same safety as the episodic tier: every write passes the Write Gate, and the SQLite
index (knowledge.sqlite) is a throwaway rebuildable view of the append-only markdown
source of truth (reversible reconciliation). The brief layer reads BOTH tiers: recent
specific lessons AND the distilled principles.
"""

from __future__ import annotations
import re
import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, asdict

from desk.memory.write_gate import check_lesson, WriteGateError
from desk.memory import store
from desk.agents import llm

MEM_DIR = Path(__file__).resolve().parent
KNOW_DIR = MEM_DIR / "knowledge"
KNOW_DB = MEM_DIR / "knowledge.sqlite"
MIN_EVIDENCE = 2            # a principle needs >=2 supporting lessons before it's trusted
GLOBAL_MIN_EVIDENCE = 4    # a CROSS-CITY meta-principle needs more corroboration than a per-city one
CONF_SATURATION = 6.0      # evidence count at which confidence ~saturates toward 1.0

KNOW_DIR.mkdir(parents=True, exist_ok=True)

_NOTE_RE = re.compile(
    r"^## PRINCIPLE (?P<ts>\S+) \| category: (?P<category>[^\|]+?) \| topic: (?P<topic>.+)$",
    re.MULTILINE,
)

_SYSTEM = (
    "You distil many specific FAKE-MONEY weather-trading lessons into ONE general, "
    "reusable principle. Be concrete and actionable. You may never advocate real "
    "money, wallets, ignoring model disagreement, or betting the whole bankroll. "
    "Output strict JSON: {\"claim\": <one-sentence principle>, \"tags\": [..]}"
)


@dataclass
class Principle:
    ts: str
    category: str
    topic: str            # the semantic cluster key, e.g. "model_disagreement"
    claim: str            # the generalized principle
    confidence: float     # 0..1, grows with evidence_count
    evidence_count: int
    outcomes: str         # e.g. "LOST:4,WON:1"
    tags: str

    def to_markdown(self) -> str:
        return (
            f"## PRINCIPLE {self.ts} | category: {self.category} | topic: {self.topic}\n"
            f"- claim: {self.claim}\n"
            f"- confidence: {self.confidence}\n"
            f"- evidence_count: {self.evidence_count}\n"
            f"- outcomes: {self.outcomes}\n"
            f"- tags: {self.tags}\n\n"
        )

    def as_dict(self) -> dict:
        return asdict(self)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _category_file(category: str) -> Path:
    safe = re.sub(r"[^a-z0-9_-]", "-", category.lower())
    return KNOW_DIR / f"{safe}.md"


def _primary_tag(tags: str) -> str:
    """The first non-outcome tag is the semantic cluster key for a lesson."""
    skip = {"won", "lost", "void", "unresolved", "edge_confirmed"}
    for t in (tags or "").split(","):
        t = t.strip().lower()
        if t and t not in skip:
            return t
    return "general"


def _confidence(evidence_count: int, loss_share: float) -> float:
    """Confidence grows with evidence and with how one-sided the outcomes are.

    A principle backed by 6 lessons that all point the same way is trustworthy; one
    backed by 2 mixed lessons is not. Bounded to [0,1].
    """
    breadth = min(1.0, evidence_count / CONF_SATURATION)      # more evidence -> higher
    decisiveness = abs(loss_share - 0.5) * 2.0                # 0 (50/50) .. 1 (one-sided)
    return round(0.25 + 0.55 * breadth + 0.20 * decisiveness, 3)


# --------------------------------------------------------------------------- #
# WRITE
# --------------------------------------------------------------------------- #
def _append_principle(p: Principle) -> Path:
    # reuse the episodic Write Gate by mapping the principle onto its lesson-shaped
    # fields (rule == the claim) so the same poison filters apply.
    check_lesson({"thesis": p.topic, "root_cause": "", "rule": p.claim, "tags": p.tags})
    path = _category_file(p.category)
    with path.open("a", encoding="utf-8") as f:
        f.write(p.to_markdown())
    return path


# --------------------------------------------------------------------------- #
# CONSOLIDATE — episodic lessons -> semantic principles (the reflection step)
# --------------------------------------------------------------------------- #
def _latest_principles() -> dict:
    """Map (category, topic) -> latest stored principle dict (to detect changes)."""
    latest: dict[tuple, dict] = {}
    for md in KNOW_DIR.glob("*.md"):
        text = md.read_text(encoding="utf-8")
        for blk in re.split(r"(?=^## PRINCIPLE )", text, flags=re.MULTILINE):
            m = _NOTE_RE.search(blk)
            if not m:
                continue
            fields = {"ts": m.group("ts"), "category": m.group("category").strip(),
                      "topic": m.group("topic").strip()}
            for key in ("claim", "confidence", "evidence_count", "outcomes", "tags"):
                fm = re.search(rf"^- {key}: (.*)$", blk, flags=re.MULTILINE)
                fields[key] = fm.group(1).strip() if fm else ""
            latest[(fields["category"], fields["topic"])] = fields
    return latest


def _synthesize_claim(category: str, topic: str, rules: list, outcomes: str) -> tuple:
    """Generalize a cluster of lesson rules into one principle claim + tags.

    Uses the LLM seam (deep tier) when a real backend is available; otherwise the
    heuristic picks the most representative rule verbatim. Both are Write-Gate-safe.
    """
    # heuristic default: the most frequent rule text is already a generalization.
    freq = defaultdict(int)
    for r in rules:
        freq[r] += 1
    heuristic_claim = max(freq, key=freq.get) if freq else ""
    heuristic_tags = [topic]

    try:
        user = ("```facts\n" + json.dumps(
            {"category": category, "topic": topic, "outcomes": outcomes,
             "lesson_rules": rules[:12]}, indent=2) + "\n```\nReturn the JSON.")
        raw = llm.complete(_SYSTEM, user, want_json=True, tier="deep")
        data = json.loads(raw)
        if data.get("_backend") == "mock" or not data.get("claim"):
            return heuristic_claim, heuristic_tags
        tags = data.get("tags") if isinstance(data.get("tags"), list) else [topic]
        if topic not in tags:
            tags = [topic, *tags]
        return data["claim"].strip(), tags
    except Exception:
        return heuristic_claim, heuristic_tags


def consolidate() -> dict:
    """Distil all episodic lessons into semantic principles. Idempotent per cycle.

    Returns a summary {clusters, written, unchanged, blocked}.
    """
    # gather lessons grouped by (category, primary tag)
    clusters: dict[tuple, list] = defaultdict(list)
    losing: list = []
    for md in store.LESSONS_DIR.glob("*.md"):
        for f in store._parse_lessons_file(md):
            key = (f["category"], _primary_tag(f.get("tags", "")))
            clusters[key].append(f)
            if (f.get("outcome") or "").upper() == "LOST":
                losing.append(f)

    # CROSS-CITY META TIER: the brain's biggest recurring mistake, generalized across
    # ALL cities. The per-city tier above never fires while each city has <2 lessons,
    # so a pattern repeated once-per-city in five different cities would go unlearned.
    # LLM-emitted tag strings are too noisy to cluster on (tail-risk vs tail-events vs
    # coastal-capping), so we group by OUTCOME and let the deep model distil the common
    # thread. This is what lets the brain generalize a mistake it keeps repeating.
    if len(losing) >= GLOBAL_MIN_EVIDENCE:
        clusters[("global", "recurring-loss-pattern")] = losing

    latest = _latest_principles()
    written = unchanged = blocked = 0

    for (category, topic), lessons in clusters.items():
        if len(lessons) < MIN_EVIDENCE:
            continue
        n = len(lessons)
        losses = sum(1 for l in lessons if (l.get("outcome") or "").upper() == "LOST")
        wins = sum(1 for l in lessons if (l.get("outcome") or "").upper() == "WON")
        loss_share = losses / n if n else 0.0
        conf = _confidence(n, loss_share)
        outcomes = f"LOST:{losses},WON:{wins}"

        prev = latest.get((category, topic))
        # idempotency: skip if evidence count and outcomes are unchanged since last note
        if prev and prev.get("evidence_count") == str(n) and prev.get("outcomes") == outcomes:
            unchanged += 1
            continue

        rules = [l.get("rule", "") for l in lessons if l.get("rule")]
        claim, tags = _synthesize_claim(category, topic, rules, outcomes)
        if not claim:
            continue
        p = Principle(ts=_now_iso(), category=category, topic=topic, claim=claim,
                      confidence=conf, evidence_count=n, outcomes=outcomes,
                      tags=",".join(tags))
        try:
            _append_principle(p)
            written += 1
        except WriteGateError:
            blocked += 1

    rebuild_knowledge_index()
    return {"clusters": len(clusters), "written": written,
            "unchanged": unchanged, "blocked": blocked}


# --------------------------------------------------------------------------- #
# RECONCILE + READ
# --------------------------------------------------------------------------- #
def rebuild_knowledge_index(db_path: Path = KNOW_DB) -> int:
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.execute("""
        CREATE TABLE principles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT, category TEXT, topic TEXT, claim TEXT,
            confidence REAL, evidence_count INTEGER, outcomes TEXT, tags TEXT
        )""")
    con.execute("CREATE INDEX idx_pcat ON principles(category)")
    n = 0
    for md in sorted(KNOW_DIR.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        for blk in re.split(r"(?=^## PRINCIPLE )", text, flags=re.MULTILINE):
            m = _NOTE_RE.search(blk)
            if not m:
                continue
            g = {"ts": m.group("ts"), "category": m.group("category").strip(),
                 "topic": m.group("topic").strip()}
            for key in ("claim", "confidence", "evidence_count", "outcomes", "tags"):
                fm = re.search(rf"^- {key}: (.*)$", blk, flags=re.MULTILINE)
                g[key] = fm.group(1).strip() if fm else ""
            con.execute(
                "INSERT INTO principles (ts,category,topic,claim,confidence,"
                "evidence_count,outcomes,tags) VALUES (?,?,?,?,?,?,?,?)",
                (g["ts"], g["category"], g["topic"], g["claim"],
                 float(g["confidence"] or 0), int(g["evidence_count"] or 0),
                 g["outcomes"], g["tags"]))
            n += 1
    con.commit()
    con.close()
    return n


def recall_knowledge(category: str, limit: int = 3, db_path: Path = KNOW_DB) -> list[dict]:
    """Return the strongest distilled PRINCIPLES for a category.

    Keeps only the latest note per topic (semantic memory converges), then ranks by
    confidence. This is the high-signal layer the brief consults alongside lessons.
    """
    if not db_path.exists():
        rebuild_knowledge_index(db_path)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    # ts DESC, then evidence_count DESC so that when two notes for a topic share a
    # timestamp (same-second consolidations) the stronger, higher-evidence one wins.
    rows = con.execute(
        "SELECT * FROM principles WHERE category=? "
        "ORDER BY ts DESC, evidence_count DESC", (category,)
    ).fetchall()
    con.close()
    seen, latest = set(), []
    for r in rows:                       # rows are newest-first; keep first per topic
        d = dict(r)
        if d["topic"] in seen:
            continue
        seen.add(d["topic"])
        latest.append(d)
    latest.sort(key=lambda d: d["confidence"], reverse=True)
    return latest[:limit]


if __name__ == "__main__":
    print("consolidate:", json.dumps(consolidate(), indent=2))
    print("knowledge indexed:", rebuild_knowledge_index())
