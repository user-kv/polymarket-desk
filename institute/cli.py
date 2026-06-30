"""institute CLI — A1: map | classify | status.  A2: gate.  A3: propose | pipeline | paper.  A4: book.  A5: crypto-snapshot | crypto-settle.  A6: forecast | cycle.  B1: cpi-snapshot | cpi-settle.

    python -m institute.cli map              # build & print the predictability map
    python -m institute.cli classify "<question>"
    python -m institute.cli status
    python -m institute.cli gate <archetype> <baseline>
    python -m institute.cli propose          # propose strategies from the map
    python -m institute.cli pipeline         # run cells through Gates 1-3
    python -m institute.cli paper            # show open paper positions
    python -m institute.cli book             # build the risk-managed book (Gates 4-7)
    python -m institute.cli crypto-snapshot  # snapshot live crypto-daily markets
    python -m institute.cli crypto-settle    # settle open crypto markets past end_date
    python -m institute.cli forecast         # forecast open markets (Alpha Engine, A6)
    python -m institute.cli cycle            # full cadence loop: forecast + book (A6)
    python -m institute.cli cpi-snapshot     # snapshot live US CPI MoM markets (B1)
    python -m institute.cli cpi-settle       # settle open CPI markets past end_date (B1)
"""
import os
import sys

from institute.classify.archetype import classify, in_initial_universe
from institute import resolve as _resolve
from institute.map import predictability

BASE = os.path.dirname(os.path.dirname(__file__))
MAP_OUT = os.path.join(os.path.dirname(__file__), "data", "predictability_map.json")


def cmd_map():
    rows = _resolve.load_all_rows()
    cells = predictability.build(rows)
    predictability.write_map(cells, MAP_OUT)
    print(predictability.render(cells))
    print(f"\n{len(rows)} resolved rows  ->  {MAP_OUT}")


def cmd_classify(q):
    a = classify(q)
    print(f"{a}  (initial-universe: {in_initial_universe(a)})")


def cmd_status():
    from institute.resolve import weather_adapter, crypto_adapter
    from institute.sensor.crypto import CRYPTO_STORE
    weather_rows = weather_adapter.load_rows()
    crypto_rows = crypto_adapter.load_rows()
    total = len(weather_rows) + len(crypto_rows)
    crypto_exists = os.path.exists(CRYPTO_STORE)
    print(f"resolved rows: {total}  | archetypes wired: weather-daily, crypto-daily")
    print(f"  weather settled: {len(weather_rows)}")
    print(f"  crypto store: {'present' if crypto_exists else 'not found'} | settled: {len(crypto_rows)}")
    print(f"map output: {MAP_OUT} ({'exists' if os.path.exists(MAP_OUT) else 'not built'})")


def cmd_gate(archetype, baseline_name):
    from institute.evidence import gate1
    rows = _resolve.load_all_rows()
    result = gate1.run_gate(archetype, baseline_name, rows=rows)
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
    rows = _resolve.load_all_rows()
    results = pipeline.run_all(rows=rows)
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


def cmd_book():
    from institute.portfolio import book
    rows = _resolve.load_all_rows()
    b = book.build_book(rows=rows)
    print(book.render(b))


def cmd_crypto_snapshot():
    from institute.sensor import crypto
    new = crypto.snapshot()
    if new:
        print(f"snapshotted {len(new)} live crypto markets -> {crypto.CRYPTO_STORE}")
    else:
        print("no new live crypto-daily markets found")


def cmd_crypto_settle():
    from institute.sensor import crypto
    done = crypto.settle()
    print(f"settled {len(done)} crypto markets")


def cmd_cpi_snapshot():
    """B1: snapshot live US CPI MoM range markets from Gamma."""
    from institute.verticals.cpi import sensor as cpi_sensor
    new = cpi_sensor.snapshot()
    print(f"snapshotted {len(new)} CPI range markets")


def cmd_cpi_settle():
    """B1: settle open CPI markets past end_date using BLS data."""
    from institute.verticals.cpi import sensor as cpi_sensor
    done = cpi_sensor.settle()
    print(f"settled {len(done)} CPI markets")


def _live_forecast_enabled():
    """A real forecast is only honest if a real model is behind the seam.

    forecast_open() is idempotent: the FIRST forecast on a market is frozen
    forever (point-in-time integrity). So writing a deterministic placeholder
    (mock) forecast onto a live market permanently BURNS that irreplaceable
    slot with a number we do not believe. We therefore refuse to forecast
    unless INSTITUTE_LIVE_FORECAST is explicitly set -- a single, auditable
    cord to pull once the real provider is wired behind agents/llm.complete.
    """
    import os
    return os.environ.get("INSTITUTE_LIVE_FORECAST", "").strip().lower() in ("1", "true", "yes")


def cmd_forecast():
    """A6: forecast open markets via the Alpha Engine across all wired stores."""
    if not _live_forecast_enabled():
        print("forecast skipped: INSTITUTE_LIVE_FORECAST not set "
              "(refusing to freeze placeholder forecasts on live markets)")
        return

    from institute.alpha.forecast_store import forecast_open
    from institute.sensor.crypto import CRYPTO_STORE

    stores = {"crypto": CRYPTO_STORE}
    total = 0
    for label, path in stores.items():
        newly = forecast_open(path, mock=False)
        total += len(newly)
        print(f"forecast {len(newly)} open markets across {label}")
    if not total:
        print("forecast 0 open markets across all stores")


def cmd_cycle():
    """A6: full cadence loop — forecast open markets, then build the book."""
    from institute import cadence
    from institute.portfolio import book as _book

    live = _live_forecast_enabled()
    out = cadence.run_cycle(mock=not live, forecast=live)
    rendered = _book.render(out["book"])
    assert rendered.isascii(), "render() produced non-ASCII output"
    print(rendered)


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
    elif cmd == "book":
        cmd_book()
    elif cmd == "crypto-snapshot":
        cmd_crypto_snapshot()
    elif cmd == "crypto-settle":
        cmd_crypto_settle()
    elif cmd == "forecast":
        cmd_forecast()
    elif cmd == "cycle":
        cmd_cycle()
    elif cmd == "cpi-snapshot":
        cmd_cpi_snapshot()
    elif cmd == "cpi-settle":
        cmd_cpi_settle()
    else:
        cmd_status()


if __name__ == "__main__":
    main()
