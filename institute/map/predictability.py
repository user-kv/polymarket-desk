"""Build the predictability map: archetype × baseline → measured edge.

A1's headline deliverable. Status colours a cell green only when it shows
positive market-relative skill AND positive EV_net over enough samples — a
deliberately conservative first cut (real promotion needs the 7-gate stack).
"""
import os
import json
from collections import defaultdict

from institute.map import baselines as B
from institute.corpus.schema import MapCell

MIN_N_GREEN = 30  # below this, edge is unproven → grey at best


def build(rows, min_n_green=MIN_N_GREEN):
    by_arch = defaultdict(list)
    for r in rows:
        by_arch[r["archetype"]].append(r)

    cells = []
    for arch, arch_rows in sorted(by_arch.items()):
        for name, (fn, kw, use_realized) in B.BASELINES.items():
            m = B.evaluate(arch_rows, fn, use_realized=use_realized, **kw)
            cells.append(MapCell(
                archetype=arch, baseline=name, n=m["n"], win_pct=m["win_pct"],
                mean_S=m["mean_S"], ev_net=m["ev_net"], naive_roi=m["naive_roi"],
                status=_status(m, min_n_green),
            ))
    return cells


def _status(m, min_n_green):
    if m["ev_net"] > 0 and m["mean_S"] > 0:
        return "green" if m["n"] >= min_n_green else "grey"
    if m["ev_net"] > 0 or m["mean_S"] > 0:
        return "grey"
    return "red"


def write_map(cells, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {"cells": [c.dict() for c in cells]}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return path


def render(cells):
    lines = [f"{'archetype':<16} {'baseline':<14} {'n':>4} {'win%':>6} {'meanS':>8} {'EV_net':>8}  status"]
    for c in cells:
        lines.append(f"{c.archetype:<16} {c.baseline:<14} {c.n:>4} {c.win_pct:>6} "
                     f"{c.mean_S:>8} {c.ev_net:>8}  {c.status}")
    return "\n".join(lines)
