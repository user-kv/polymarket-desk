"""
desk/memory/write_gate.py — the memory Write Gate (research round 1 / SSGM).

Before any lesson is stored, it must pass this gate. The gate blocks the
memory-poisoning / goal-drift failure mode: a self-written autopsy could otherwise
"learn" a lesson like "ignore model disagreement" or "bet 100% of bankroll", and
that poisoned semantic memory would steer every future trade.

The gate is deterministic (no LLM needed to verify it) and checks a proposed lesson
against the IMMUTABLE kernel facts:
  * it must not advocate real money / wallets / live orders,
  * it must not advocate deleting or inverting a discipline rule,
  * if it proposes a parameter change, that change must stay within kernel bounds.
"""

from __future__ import annotations
import re
from desk.kernel import invariants as inv


class WriteGateError(Exception):
    """Raised when a proposed lesson would contradict a protected kernel fact."""


# phrases that would steer the system toward a kernel violation
_BANNED_PATTERNS = [
    r"\breal money\b", r"\breal[- ]?world (order|bet)s?\b", r"\blive order\b",
    r"\bwallet\b", r"\bprivate key\b", r"\bapi key\b",
    r"\bignore (the )?(model|ensemble) (dis)?agreement\b",
    r"\bdisable (the )?\w+ rule\b", r"\bdrop (the )?\w+ rule\b",
    r"\bbet (the )?(whole|entire|full|100%|all) (of )?(the )?bankroll\b",
    r"\bremove the (edge|time|agreement|buffer|bankroll) (rule|check)\b",
]

# "set edge_threshold_pct to 1.0" style directives we must bounds-check
_PARAM_SET_RE = re.compile(
    r"\b(?P<key>[a-z_]+)\s*(?:=|to|:)\s*(?P<val>-?\d+(?:\.\d+)?)", re.IGNORECASE
)


def check_lesson(lesson: dict) -> None:
    """Raise WriteGateError if the lesson would poison memory; else return None."""
    blob = " ".join(str(lesson.get(k, "")) for k in
                    ("thesis", "root_cause", "rule", "tags")).lower()

    for pat in _BANNED_PATTERNS:
        if re.search(pat, blob):
            raise WriteGateError(
                f"Write Gate REJECT: lesson advocates a kernel violation (matched /{pat}/)."
            )

    # any "param = value" the lesson proposes must respect kernel bounds
    for m in _PARAM_SET_RE.finditer(blob):
        key = m.group("key")
        if key in inv.PARAM_BOUNDS:
            val = float(m.group("val"))
            if not inv.param_within_bounds(key, val):
                b = inv.PARAM_BOUNDS[key]
                raise WriteGateError(
                    f"Write Gate REJECT: lesson sets {key}={val} outside protected "
                    f"bound [{b['min']}, {b['max']}]."
                )

    # a stored lesson must actually carry a generalized rule (Reflexion needs the
    # 'semantic gradient' — an empty rule is noise, not a lesson)
    if not lesson.get("rule", "").strip():
        raise WriteGateError("Write Gate REJECT: lesson has no generalized 'rule'.")
