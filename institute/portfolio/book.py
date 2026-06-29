"""Portfolio book orchestrator: cells -> eligible -> allocation (CONSTITUTION Gates 4-7, §7).

build_book() is the top-level entry point. With today's data the live book is
correctly all-reserve (weather cell is gate1_insufficient) -- that is the system
working, not a failure.
"""
from institute.resolve import weather_adapter
from institute import pipeline
from institute.map.baselines import evaluate, longshot_fade, BASELINES
from institute.portfolio import gate4, allocator


def _mean_price_for_cell(rows, archetype, baseline_name):
    """Compute mean executable entry price for the bet side taken by this baseline.

    For NO bets: price = 1 - q_yes. For YES bets: price = q_yes.
    Returns 0.5 if no bets are placed (safe default -- Kelly will be 0 anyway).
    """
    arch_rows = [rm for rm in rows if rm.get("archetype") == archetype]
    if not arch_rows:
        return 0.5

    # Resolve the baseline function
    if baseline_name in BASELINES:
        fn, kw, _ = BASELINES[baseline_name]
    else:
        return 0.5

    prices = []
    for rm in arch_rows:
        p, side = fn(rm, **kw)
        if side is None:
            continue
        q_yes = rm["q_yes"]
        if side == "NO":
            prices.append(1.0 - q_yes)
        else:
            prices.append(q_yes)

    if not prices:
        return 0.5
    return sum(prices) / len(prices)


def build_book(rows=None, bankroll=10000.0, use_llm=False, log=False):
    """Build the risk-managed book from all cells that pass Gates 1-4.

    Returns dict with keys: eligible, gate4 (status dicts for paper cells),
    allocation (full allocator output).
    """
    if rows is None:
        rows = weather_adapter.load_rows()

    results = pipeline.run_all(rows=rows, use_llm=use_llm, log=log)

    # Collect cells that have status == "paper" (gates 1-3 cleared AND gate1 passed)
    paper_cells = [r for r in results if r["status"] == "paper"]

    gate4_statuses = []
    eligible_cells = []

    for r in paper_cells:
        strat = r["strategy"]
        g4 = gate4.gate4_status(strat.id)
        gate4_statuses.append(g4)

        if g4["verdict"] != "graduated":
            continue

        # Build the allocator cell dict from strategy + map.baselines.evaluate metrics
        arch_rows = [rm for rm in rows if rm.get("archetype") == strat.archetype]
        if strat.baseline in BASELINES:
            fn, kw, _ = BASELINES[strat.baseline]
        else:
            continue

        metrics = evaluate(arch_rows, fn, **kw)
        mean_price = _mean_price_for_cell(rows, strat.archetype, strat.baseline)

        eligible_cells.append({
            "id": strat.id,
            "archetype": strat.archetype,
            "baseline": strat.baseline,
            "metrics": metrics,
            "mean_price": mean_price,
        })

    alloc = allocator.allocate(eligible_cells, bankroll)

    return {
        "eligible": [c["id"] for c in eligible_cells],
        "gate4": gate4_statuses,
        "allocation": alloc,
    }


def render(book):
    """Render the book as an ASCII table. Must be .isascii() clean.

    Shows allocation details when cells have graduated, otherwise reports
    an all-reserve book.
    """
    alloc = book["allocation"]
    bankroll = alloc["bankroll"]
    deployed = alloc["deployed"]
    reserve = alloc["reserve"]
    halt = alloc["book_drawdown_halt"]
    allocations = alloc["allocations"]

    lines = []
    lines.append("=" * 76)
    lines.append("  RISK-MANAGED BOOK  (Gates 4-7)")
    lines.append("-" * 76)

    if not allocations:
        lines.append("  (no cells graduated to capital -- book is all reserve)")
    else:
        header = f"  {'id':<14}{'archetype':<16}{'baseline':<16}{'weight':>7}  {'dollars':>9}  {'status'}"
        lines.append(header)
        lines.append("-" * 76)
        for a in allocations:
            lines.append(
                f"  {a['id']:<14}{a['archetype']:<16}{a['baseline']:<16}"
                f"{a['weight']:>7.4f}  {a['dollars']:>9.2f}  {a['status']}"
            )

    lines.append("-" * 76)
    lines.append(f"  bankroll:  ${bankroll:,.2f}")
    lines.append(f"  deployed:  ${deployed:,.2f}")
    lines.append(f"  reserve:   ${reserve:,.2f}")
    lines.append(f"  book drawdown halt: {halt:.0%}")
    lines.append("=" * 76)

    result = "\n".join(lines)
    # Safety check: guarantee ASCII-only on Windows cp1252
    assert result.isascii(), "render() produced non-ASCII output"
    return result
