"""Coverage report: where is the PROVABLE data in the ~387k resolved-market corpus?

Buckets every stored market by venue x vertical x liquidity, so the design phase knows which
verticals have enough backtestable ground truth and which are data-starved. Writes both a
human-readable report and a machine-readable JSON for Fable 5 / downstream tooling.

Reads:  institute/data/history/*.jsonl
Writes: institute/data/history/coverage_report.md
        institute/data/history/coverage_report.json

stdlib only. ASCII output. Usage:
    python coverage_report.py
"""
import json
import os
import re
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "history")

# Vertical classifier: ordered rules, first match wins. Mirrors the institute's
# market-universe families (PLAN/01). Patterns are lowercase substrings/regex.
RULES = [
    ("weather", re.compile(r"temperature|high temp|weather|rain|snowfall|hurricane|heat index|\bhighest? in\b.*\bon\b|degrees")),
    ("macro_econ", re.compile(r"\bcpi\b|inflation|fed(eral)? (funds|reserve)|rate (hike|cut|decision)|interest rate|nonfarm|payroll|unemployment|jobs report|\bgdp\b|recession|treasury|fomc")),
    ("crypto_price", re.compile(r"bitcoin|\bbtc\b|ethereum|\beth\b|solana|\bsol\b|dogecoin|crypto|\bfdv\b|token|coin.*(above|below|reach|hit|price)|(above|below|hit|reach).*\$")),
    ("politics_us", re.compile(r"president|election|nominee|senate|governor|congress|electoral|primary|caucus|trump|biden|harris|dnc|rnc|approval rating|cabinet|supreme court|impeach")),
    ("geopolitics", re.compile(r"ceasefire|war\b|invasion|ukraine|russia|israel|gaza|iran|north korea|taiwan|nato|sanctions|missile|nuclear|coup|treaty|hostage")),
    ("sports", re.compile(r"\bvs\.?\b|\bbeat\b|\bwin (the )?(game|match|series|cup|bowl|finals|championship)\b|nba|nfl|mlb|nhl|ncaa|premier league|la liga|serie a|champions league|world cup|ufc|f1|grand prix|tennis|golf|super bowl|playoffs|spread:|o/u|moneyline")),
    ("esports", re.compile(r"cs2|csgo|counter-strike|dota|league of legends|\blol\b.*(match|win)|valorant|overwatch|esports")),
    ("entertainment", re.compile(r"oscar|grammy|emmy|box office|album|movie|film|billboard|spotify|rotten tomatoes|bachelor|survivor|big brother|time person")),
    ("science_health", re.compile(r"\bfda\b|drug|vaccine|approval|clinical|pandemic|virus|spacex|nasa|launch|rocket|asteroid|climate")),
    ("company_tech", re.compile(r"\bipo\b|stock|earnings|apple|tesla|google|openai|gpt|nvidia|microsoft|amazon|meta\b|twitter|\bx\b.*musk|ceo|acquisition|bankrupt")),
]

# Liquidity tiers by reported volume (Polymarket Gamma) — CLOB rows have no volume field,
# so those are tiered by trade count when price data exists, else "unknown".
def vol_tier(vol):
    if vol is None:
        return "unknown"
    try:
        v = float(vol)
    except (TypeError, ValueError):
        return "unknown"
    if v >= 100000: return "high(100k+)"
    if v >= 10000:  return "mid(10k+)"
    if v >= 1000:   return "low(1k+)"
    return "thin(<1k)"


# Kalshi ships its own category labels; map them onto our verticals (better than regex).
KALSHI_CATEGORY_MAP = {
    "Crypto": "crypto_price",
    "Sports": "sports",
    "Financials": "financials",
    "Entertainment": "entertainment",
    "Mentions": "entertainment",
    "Climate and Weather": "weather",
    "Elections": "politics_us",
    "Politics": "politics_us",
    "Commodities": "commodities",
    "Economics": "macro_econ",
    "Science and Technology": "science_health",
    "Health": "science_health",
    "Companies": "company_tech",
    "World": "geopolitics",
    "Social": "entertainment",
    "Transportation": "other",
}


def classify(question, native_category=None):
    if native_category:
        mapped = KALSHI_CATEGORY_MAP.get(native_category)
        if mapped:
            return mapped
    q = (question or "").lower()
    for name, pat in RULES:
        if pat.search(q):
            return name
    return "other"


def iter_store(fname, venue_label):
    path = os.path.join(DATA, fname)
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                m = json.loads(line)
            except Exception:
                continue
            yield venue_label, m


def main():
    t0 = time.time()
    # counts[venue][vertical] = {"n": int, "tiers": {tier: int}}
    counts = {}
    price_index = {}
    # trade-count index from the price store (which markets are actually backtestable)
    ppath = os.path.join(DATA, "prices", "polymarket_trades.jsonl")
    if os.path.exists(ppath):
        with open(ppath, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    price_index[str(r.get("id"))] = r.get("n_trades", 0)
                except Exception:
                    pass

    sources = [
        ("polymarket_resolved.jsonl", "polymarket"),
        ("polymarket_clob_resolved.jsonl", "polymarket"),
        ("kalshi_settled.jsonl", "kalshi"),
    ]
    total = 0
    priced_by_vertical = {}
    for fname, venue in sources:
        for venue_label, m in iter_store(fname, venue):
            total += 1
            vert = classify(m.get("question"),
                            m.get("category") if venue_label == "kalshi" else None)
            tier = vol_tier(m.get("volume"))
            v = counts.setdefault(venue_label, {}).setdefault(vert, {"n": 0, "tiers": {}})
            v["n"] += 1
            v["tiers"][tier] = v["tiers"].get(tier, 0) + 1
            nt = price_index.get(str(m.get("id")))
            if nt is not None:
                pv = priced_by_vertical.setdefault(vert, {"priced": 0, "usable": 0})
                pv["priced"] += 1
                if nt >= 10:
                    pv["usable"] += 1

    # ---- write JSON ----
    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_markets": total,
        "by_venue_vertical": counts,
        "price_series": {
            "total_priced": len(price_index),
            "usable_10plus_trades": sum(1 for n in price_index.values() if n >= 10),
            "by_vertical": priced_by_vertical,
        },
        "classifier_note": "first-match regex rules over question text; 'other' = no rule hit",
    }
    jpath = os.path.join(DATA, "coverage_report.json")
    json.dump(out, open(jpath, "w", encoding="utf-8"), indent=1)

    # ---- write markdown ----
    lines = []
    lines.append("# Coverage Report — where the provable data is")
    lines.append("")
    lines.append(f"Generated {out['generated_at']} over {total:,} resolved markets.")
    lines.append("")
    for venue in sorted(counts):
        lines.append(f"## {venue}")
        lines.append("")
        lines.append("| vertical | markets | high(100k+) | mid(10k+) | low(1k+) | thin(<1k) | unknown |")
        lines.append("|---|---|---|---|---|---|---|")
        for vert, v in sorted(counts[venue].items(), key=lambda kv: -kv[1]["n"]):
            t = v["tiers"]
            lines.append("| {} | {:,} | {:,} | {:,} | {:,} | {:,} | {:,} |".format(
                vert, v["n"],
                t.get("high(100k+)", 0), t.get("mid(10k+)", 0),
                t.get("low(1k+)", 0), t.get("thin(<1k)", 0), t.get("unknown", 0)))
        lines.append("")
    lines.append("## Decision-time price series (Polymarket, from real trades)")
    lines.append("")
    lines.append(f"- markets priced: {len(price_index):,}")
    lines.append(f"- usable (>=10 trades): {out['price_series']['usable_10plus_trades']:,}")
    lines.append("")
    if priced_by_vertical:
        lines.append("| vertical | priced | usable(>=10 trades) |")
        lines.append("|---|---|---|")
        for vert, pv in sorted(priced_by_vertical.items(), key=lambda kv: -kv[1]["priced"]):
            lines.append(f"| {vert} | {pv['priced']:,} | {pv['usable']:,} |")
        lines.append("")
    lines.append("## Reading guide")
    lines.append("- 'unknown' volume = CLOB-sourced rows (no volume field); their liquidity is")
    lines.append("  judged by trade count once priced.")
    lines.append("- A vertical is PROVABLE when it has both (a) enough resolved markets and")
    lines.append("  (b) enough of them with usable price series or an external ground-truth")
    lines.append("  signal (weather: Open-Meteo; macro: FRED/BLS) that does not need venue prices.")
    lines.append("- Kalshi rows have no venue volume in our pull; depth there = market count +")
    lines.append("  the venue's robust-FLB literature. Kalshi candlestick pricing = future work.")
    mpath = os.path.join(DATA, "coverage_report.md")
    open(mpath, "w", encoding="utf-8").write("\n".join(lines) + "\n")

    print(f"scanned {total:,} markets in {time.time()-t0:.1f}s")
    print(f"wrote {os.path.relpath(mpath, HERE)} and .json")


if __name__ == "__main__":
    main()
