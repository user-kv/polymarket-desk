"""
desk/digest.py — the daily change digest (guardrail #6, research round 3/4).

Because there is no human approval gate, this is your after-the-fact review: a short
summary of everything the desk did to itself and learned in the last 24h. Reading it
each morning keeps an autonomous system legible — and anything you dislike is one
`git revert` away (guardrail #2).

When Anthropic OpenTelemetry is configured on the VPS, the same numbers feed a live
cost/observability dashboard; this file is the offline, always-available version.
"""

from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

from desk import overseer, risk
from desk.memory import store

DESK = Path(__file__).resolve().parent


def _recent_lessons(hours: int = 24) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    out = []
    for md in (DESK / "memory" / "lessons").glob("*.md"):
        for f in store._parse_lessons_file(md):
            try:
                t = datetime.strptime(f["ts"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            if t >= cutoff:
                out.append(f)
    return out


def _recent_promotions(hours: int = 24) -> list[str]:
    log = overseer.PROMOTIONS_LOG
    if not log.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    lines = []
    for line in log.read_text(encoding="utf-8").splitlines():
        try:
            t = datetime.strptime(line.split(" | ")[0], "%Y-%m-%d %H:%M:%SZ").replace(tzinfo=timezone.utc)
        except (ValueError, IndexError):
            continue
        if t >= cutoff:
            lines.append(line)
    return lines


def build_digest(hours: int = 24) -> dict:
    cfg = overseer.load_config()
    kernel_ok, kernel_msg = overseer.inv.verify_kernel_integrity()
    lessons = _recent_lessons(hours)
    return {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_hours": hours,
        "kernel_intact": kernel_ok,
        "kernel_msg": kernel_msg,
        "self_modification_enabled": cfg.get("self_modification_enabled", False),
        "lessons_added": len(lessons),
        "lessons": [{"category": l["category"], "outcome": l["outcome"],
                     "rule": l["rule"]} for l in lessons],
        "tools_promoted": _recent_promotions(hours),
        "category_winrates": {c: s["winrate"] for c, s in risk.all_category_winrates().items()},
    }


def render(digest: dict) -> str:
    lines = [f"# Desk daily digest — {digest['generated']} (last {digest['window_hours']}h)",
             "",
             f"- kernel intact: {digest['kernel_intact']}  ({digest['kernel_msg']})",
             f"- self-modification: {'ENABLED' if digest['self_modification_enabled'] else 'frozen (kill switch off)'}",
             f"- lessons added: {digest['lessons_added']}",
             f"- tools promoted: {len(digest['tools_promoted'])}",
             ""]
    if digest["lessons"]:
        lines.append("## New lessons")
        for l in digest["lessons"]:
            lines.append(f"- [{l['outcome']}] {l['category']}: {l['rule']}")
        lines.append("")
    if digest["tools_promoted"]:
        lines.append("## Tools promoted (review; `git revert` to undo)")
        lines += [f"- {t}" for t in digest["tools_promoted"]]
        lines.append("")
    lines.append("## Category win-rates")
    for c, w in digest["category_winrates"].items():
        lines.append(f"- {c}: {'n/a' if w is None else format(w, '.0%')}")
    return "\n".join(lines)


if __name__ == "__main__":
    d = build_digest()
    out = DESK / "digest_latest.md"
    out.write_text(render(d), encoding="utf-8")
    print(render(d))
    print(f"\n(written to {out})")
