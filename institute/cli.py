"""institute CLI — A1: map | classify | status.  A2: gate.  A3: propose | pipeline | paper.

    python -m institute.cli map        # build & print the predictability map
    python -m institute.cli classify "<question>"
    python -m institute.cli status
    python -m institute.cli gate <archetype> <baseline>
    python -m institute.cli propose    # propose strategies from the map
    python -m institute.cli pipeline   # run cells through Gates 1-3
    python -m institute.cli paper      # show open paper positions
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


def cmd_gate(archetype, baseline_name):
    from institute.evidence import gate1
    result = gate1.run_gate(archetype, baseline_name)
    print(gate1.render(result))


def cmd_propose():
    from institute.strategy import generate
    strategies = generate.propose()
    if not strategies:
        print("no strategies proposed (map shows no positive-skill cells)")
        return
    print(f"{'id':<14}{'archetype':<16}{'baseline':<18}{'mechanism'}")
    for s in strategies:
        print(f"{s.id:<14}{s.archetype:<16}{s.baseline:<18}{s.mechanism or '(none)'}")


def cmd_pipeline():
    from institute import pipeline
    results = pipeline.run_all()
    print(pipeline.render(results))


def cmd_paper():
    from institute.execute import paper
    positions = paper.open_positions()
    if not positions:
        print("no open paper positions")
        return
    seen = {}
    print(f"{'strategy_id':<14}{'archetype':<16}{'side':<6}{'q_yes':<8}{'market_id'}")
    for p in positions:
        print(f"{p['strategy_id']:<14}{p['archetype']:<16}{p['side']:<6}"
              f"{p['q_yes_entry']:<8}{p['market_id']}")
        seen[p["strategy_id"]] = p["archetype"]
    print("\nforward (settled) counts per strategy:")
    for sid in seen:
        print(f"  {sid}: {paper.forward_count(sid)}")


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    cmd = argv[0] if argv else "status"
    if cmd == "map":
        cmd_map()
    elif cmd == "classify":
        cmd_classify(argv[1] if len(argv) > 1 else "")
    elif cmd == "gate":
        archetype = argv[1] if len(argv) > 1 else "weather-daily"
        baseline = argv[2] if len(argv) > 2 else "longshot_fade"
        cmd_gate(archetype, baseline)
    elif cmd == "propose":
        cmd_propose()
    elif cmd == "pipeline":
        cmd_pipeline()
    elif cmd == "paper":
        cmd_paper()
    else:
        cmd_status()


if __name__ == "__main__":
    main()
