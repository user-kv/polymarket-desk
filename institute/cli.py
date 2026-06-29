"""institute CLI — A1: map | classify | status.

    python -m institute.cli map        # build & print the predictability map
    python -m institute.cli classify "<question>"
    python -m institute.cli status
"""
import os
import sys

from institute.classify.archetype import classify, in_initial_universe
from institute.resolve import weather_adapter
from institute.map import predictability

BASE = os.path.dirname(os.path.dirname(__file__))
MAP_OUT = os.path.join(os.path.dirname(__file__), "data", "predictability_map.json")


def cmd_map():
    rows = weather_adapter.load_rows()
    cells = predictability.build(rows)
    predictability.write_map(cells, MAP_OUT)
    print(predictability.render(cells))
    print(f"\n{len(rows)} resolved rows  ->  {MAP_OUT}")


def cmd_classify(q):
    a = classify(q)
    print(f"{a}  (initial-universe: {in_initial_universe(a)})")


def cmd_status():
    rows = weather_adapter.load_rows()
    print(f"resolved rows: {len(rows)}  | archetypes wired: weather-daily")
    print(f"map output: {MAP_OUT} ({'exists' if os.path.exists(MAP_OUT) else 'not built'})")


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    cmd = argv[0] if argv else "status"
    if cmd == "map":
        cmd_map()
    elif cmd == "classify":
        cmd_classify(argv[1] if len(argv) > 1 else "")
    else:
        cmd_status()


if __name__ == "__main__":
    main()
