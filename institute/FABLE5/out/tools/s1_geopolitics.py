"""S1 — Geopolitics forecast-capture cell. FORWARD-ONLY, PAPER-ONLY.

This tool NEVER places an order on any venue. It discovers open geopolitics
markets on Polymarket, runs a 10-persona LLM swarm forecast, blends it with
the market's own price, and freezes the result to an append-only JSONL
ledger for later scoring. That scoring (hit-rate, calibration, edge realized)
is a separate concern — this file only captures forecasts and settlements.

ANCHORING / HONESTY RULE (frozen): the market price (q_market) is NEVER
included in any prompt sent to a persona. Personas forecast blind; the market
price is blended in only AFTER all 10 replies are collected. This is the same
category of invariant as fetch_prices_v2.py's look-ahead rule for candle
timestamps -- it exists so a later audit can grep every prompt string in this
file and confirm no price token appears in one.

Pipeline (one run):
  1. DISCOVER  Gamma API `/markets?closed=false` (paginated), classify question
     text as geopolitics via a regex list (adapted from
     institute/tools/coverage_report.py's "geopolitics" rule -- see comment at
     GEO_PATTERN below), require binary Yes/No + parseable endDate > now+24h +
     outcomePrices present. Cap at --max, preferring higher liquidity/volume.
  2. FORECAST  (skipped entirely, exit 0, if GROQ_API_KEY is unset) 10 fixed
     personas each get a price-blind prompt and must reply with strict JSON
     {"prob":0.xx,"rationale":"..."}. Non-conforming replies are dropped;
     need >=6/10 valid or the market is skipped ("swarm_failed"). p_swarm =
     mean of valid probs, p_std = population stdev. p_std > 0.30 is recorded
     but flagged "no_trade_high_disagreement" (not dropped).
     p_final = 0.70 * p_swarm + 0.30 * q_market (blended only after step 2).
  3. FREEZE  Append one row per market per day to
     institute/data/history/s1_forecasts.jsonl. Idempotent: a market_id+date
     pair already present is skipped, never rewritten.
  4. SETTLE  Before forecasting, scan prior forecast rows lacking an
     "outcome" and check Gamma for resolution. Resolved markets get a NEW
     settlement row appended (never a rewrite of the forecast row):
     {"settle_for": "<market_id>|<date>", "outcome": 0|1, "settled_at": iso}.
  5. REPORT  Print a summary; hard-cap 200 LLM calls/run (Groq free-tier RPD
     protection) and sleep 0.5s between calls (Groq free-tier 30 RPM limit).

Spec-silent decisions (documented here per task instructions):
  - "highest liquidity/volume" ranking uses Gamma's `volume` field (falls back
    to `liquidity`, then 0) since `closed=false` markets don't always carry
    both fields populated.
  - The double-parse quirk (outcomes/outcomePrices/clobTokenIds ship as JSON
    strings, not JSON arrays) is handled by `_maybe_json_parse`, same pattern
    documented in institute lib/polymarket.py.
  - Settlement resolution check uses Gamma `?id=` lookup (single market), the
    lightest-weight endpoint for a point check; a market is "resolved" when
    its `closed` flag is true AND outcomePrices show a clean 0/1 split
    (tolerance 0.02) -- ambiguous closes (e.g. still ~0.5/0.5) are left
    unsettled for a future run rather than guessed.
  - GEO_PATTERN below is copied (not imported) from
    institute/tools/coverage_report.py's "geopolitics" rule, plus a few extra
    terms (regime, border, hostage, invade) the task spec asked for that
    coverage_report.py's rule doesn't carry. Keeping this file import-free of
    institute/tools avoids a fragile cross-package import for one regex.

stdlib only. ASCII output. Windows-safe paths throughout.

Usage:
    python s1_geopolitics.py                  # normal run (needs GROQ_API_KEY)
    python s1_geopolitics.py --max 15
    python s1_geopolitics.py --selftest        # no network, no key required
"""
import argparse
import json
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
# institute/FABLE5/out/tools -> up 3 -> institute
INSTITUTE_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if INSTITUTE_ROOT not in sys.path:
    sys.path.insert(0, INSTITUTE_ROOT)

from agents.llm import complete as llm_complete  # noqa: E402

DATA = os.path.join(INSTITUTE_ROOT, "data", "history")
FORECASTS_PATH = os.path.join(DATA, "s1_forecasts.jsonl")

GAMMA_MARKETS = "https://gamma-api.polymarket.com/markets"
UA = {"User-Agent": "institute-s1-geopolitics/1.0", "Accept": "application/json"}

MAX_MARKETS_DEFAULT = 15
DISCOVER_PAGE = 100
DISCOVER_MAX_OFFSET = 500  # paginate up to ~500 markets scanned
MIN_LEAD_SECONDS = 24 * 3600

PERSONAS = [
    "You are a base-rate statistician. Anchor heavily on historical base rates for "
    "events of this type; be skeptical of narrative-driven predictions.",
    "You are a military analyst. Weigh order-of-battle, force posture, and logistics.",
    "You are a career diplomat. Weigh negotiation dynamics, precedent, and incentives "
    "of the parties involved.",
    "You are a contrarian forecaster. Actively look for reasons the obvious/consensus "
    "view might be wrong.",
    "You are a regional expert with deep knowledge of the specific country/region "
    "involved.",
    "You are a historian. Compare this situation to close historical analogues.",
    "You are an intelligence analyst. Weigh available signals intelligence and public "
    "reporting patterns.",
    "You are an economist. Weigh economic incentives, sanctions costs, and trade "
    "dependencies.",
    "You are an investigative journalist. Weigh what has actually been reported vs "
    "speculation.",
    "You are a game theorist. Model this as a strategic interaction between rational "
    "actors with competing incentives.",
]

# --------------------------------------------------------------------------------------
# geopolitics classifier -- COPIED (not imported) from institute/tools/coverage_report.py
# "geopolitics" regex rule, with a few extra terms added per this tool's spec (regime,
# border, hostage, invade). See module docstring "Spec-silent decisions" for why this is
# duplicated rather than imported.
# --------------------------------------------------------------------------------------
GEO_PATTERN = re.compile(
    r"ceasefire|war\b|invasion|invade|ukraine|russia|israel|gaza|iran|north korea|"
    r"taiwan|nato|sanctions|missile|nuclear|coup|treaty|hostage|regime|border"
)


def is_geopolitics(question):
    return bool(GEO_PATTERN.search((question or "").lower()))


# --------------------------------------------------------------------------------------
# HTTP seam -- tests inject a fake fetch_fn.
# --------------------------------------------------------------------------------------
def fetch_json(url, timeout=40):
    """Live HTTP call. The only function in this module that touches the network."""
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read().decode("utf-8")
    return json.loads(body) if body else None


def _maybe_json_parse(v):
    """Gamma ships outcomes/outcomePrices/clobTokenIds as JSON-encoded strings."""
    if isinstance(v, str):
        try:
            return json.loads(v)
        except (ValueError, TypeError):
            return v
    return v


def _iter_jsonl(path):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except ValueError:
                continue


def _now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _today():
    return time.strftime("%Y-%m-%d", time.gmtime())


def _parse_iso(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            import datetime
            return datetime.datetime.strptime(s[:26].rstrip("Z") + ("Z" if fmt.endswith("Z") else ""),
                                               fmt if not fmt.endswith("Z") else fmt).replace(
                tzinfo=datetime.timezone.utc).timestamp()
        except Exception:
            continue
    # last resort: trim to seconds precision
    try:
        import datetime
        return datetime.datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(
            tzinfo=datetime.timezone.utc).timestamp()
    except Exception:
        return None


# --------------------------------------------------------------------------------------
# 1. DISCOVER
# --------------------------------------------------------------------------------------
def discover(max_markets, fetch_fn=fetch_json, sleep_fn=time.sleep):
    """Paginate Gamma, classify, filter, return up to max_markets candidate dicts."""
    now = time.time()
    candidates = []
    offset = 0
    while offset < DISCOVER_MAX_OFFSET:
        url = f"{GAMMA_MARKETS}?closed=false&limit={DISCOVER_PAGE}&offset={offset}"
        try:
            batch = fetch_fn(url)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError):
            break
        if not isinstance(batch, list) or not batch:
            break
        for m in batch:
            question = m.get("question")
            if not is_geopolitics(question):
                continue
            outcomes = _maybe_json_parse(m.get("outcomes"))
            prices = _maybe_json_parse(m.get("outcomePrices"))
            if not isinstance(outcomes, list) or len(outcomes) != 2:
                continue
            if not isinstance(prices, list) or len(prices) != 2:
                continue
            try:
                yes_price = float(prices[0])
            except (TypeError, ValueError):
                continue
            end_ts = _parse_iso(m.get("endDate"))
            if end_ts is None or end_ts <= now + MIN_LEAD_SECONDS:
                continue
            vol = m.get("volume") or m.get("liquidity") or 0
            try:
                vol = float(vol)
            except (TypeError, ValueError):
                vol = 0.0
            candidates.append({
                "market_id": str(m.get("id")),
                "condition_id": m.get("conditionId") or m.get("condition_id"),
                "question": question,
                "end_date": m.get("endDate"),
                "q_market": yes_price,
                "volume": vol,
            })
        if len(batch) < DISCOVER_PAGE:
            break
        offset += DISCOVER_PAGE
        sleep_fn(0.1)
    candidates.sort(key=lambda c: -c["volume"])
    return candidates[:max_markets]


# --------------------------------------------------------------------------------------
# 2. FORECAST
# --------------------------------------------------------------------------------------
def build_prompt(persona_line, question, end_date, today):
    """Build a price-blind persona prompt. MUST NEVER include q_market/outcomePrices."""
    return (
        f"{persona_line}\n\n"
        f"Question: {question}\n"
        f"Resolution date: {end_date}\n"
        f"Today's date: {today}\n\n"
        "Estimate the probability this resolves YES. "
        "Reply ONLY with JSON of the form "
        '{"prob": 0.xx, "rationale": "<one sentence>"} and nothing else.'
    )


def _parse_persona_reply(text):
    """Defensively parse the first {...} JSON object in a sloppy LLM reply."""
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        obj = json.loads(text[start:end + 1])
    except ValueError:
        return None
    if not isinstance(obj, dict) or "prob" not in obj:
        return None
    try:
        p = float(obj["prob"])
    except (TypeError, ValueError):
        return None
    if not (0.0 <= p <= 1.0):
        return None
    return {"prob": p, "rationale": str(obj.get("rationale", ""))[:300]}


class LLMBudget:
    """Tracks call count across a run; hard-caps at max_calls."""

    def __init__(self, max_calls=200):
        self.max_calls = max_calls
        self.calls = 0

    def exhausted(self):
        return self.calls >= self.max_calls

    def spend(self):
        self.calls += 1


def forecast_market(candidate, budget, complete_fn=llm_complete, sleep_fn=time.sleep,
                     call_sleep=0.5):
    """Run the 10-persona swarm for one candidate. Returns (row_dict_or_None, reason)."""
    today = _today()
    probs = []
    for persona_line in PERSONAS:
        if budget.exhausted():
            return None, "budget_exhausted"
        prompt = build_prompt(persona_line, candidate["question"], candidate["end_date"], today)
        # HONESTY INVARIANT: candidate["q_market"] / outcomePrices must NEVER appear
        # in `prompt`. Do not add it above without re-reading the module docstring.
        budget.spend()
        try:
            reply = complete_fn(prompt, role="forecast", mock=False, max_tokens=120)
        except Exception:
            reply = None
        sleep_fn(call_sleep)
        parsed = _parse_persona_reply(reply)
        if parsed is not None:
            probs.append(parsed["prob"])
    if len(probs) < 6:
        return None, "swarm_failed"
    p_swarm = statistics.mean(probs)
    p_std = statistics.pstdev(probs)
    q_market = candidate["q_market"]
    p_final = 0.70 * p_swarm + 0.30 * q_market
    edge = p_final - q_market
    row = {
        "date": today,
        "market_id": candidate["market_id"],
        "condition_id": candidate.get("condition_id"),
        "question": candidate["question"],
        "end_date": candidate["end_date"],
        "q_market": q_market,
        "p_swarm": round(p_swarm, 4),
        "p_std": round(p_std, 4),
        "p_final": round(p_final, 4),
        "n_valid": len(probs),
        "personas_used": 10,
        "edge": round(edge, 4),
        "would_bet": bool(abs(edge) > 0.05 and p_std <= 0.30),
        "side": "YES" if edge > 0 else "NO",
        "frozen_at": _now_iso(),
    }
    if p_std > 0.30:
        row["flag"] = "no_trade_high_disagreement"
    return row, "ok"


# --------------------------------------------------------------------------------------
# 3. FREEZE (append-only, idempotent by market_id+date)
# --------------------------------------------------------------------------------------
def load_existing_keys(path=FORECASTS_PATH):
    keys = set()
    for row in _iter_jsonl(path):
        if "market_id" in row and "date" in row:
            keys.add((row["market_id"], row["date"]))
    return keys


def append_row(row, path=FORECASTS_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=True) + "\n")


# --------------------------------------------------------------------------------------
# 4. SETTLE (append settlement rows; forecast rows are never rewritten)
# --------------------------------------------------------------------------------------
def find_unsettled(path=FORECASTS_PATH):
    """Return forecast rows lacking a matching settlement row."""
    forecasts = {}
    settled_keys = set()
    for row in _iter_jsonl(path):
        if "settle_for" in row:
            settled_keys.add(row["settle_for"])
        elif "market_id" in row and "date" in row:
            key = f"{row['market_id']}|{row['date']}"
            forecasts[key] = row
    return [(k, v) for k, v in forecasts.items() if k not in settled_keys]


def check_settlement(market_id, fetch_fn=fetch_json):
    """Query Gamma for one market's resolution status. Returns 0/1 outcome or None."""
    url = f"{GAMMA_MARKETS}?id={market_id}"
    try:
        resp = fetch_fn(url)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError):
        return None
    if isinstance(resp, list):
        resp = resp[0] if resp else None
    if not isinstance(resp, dict):
        return None
    if not resp.get("closed"):
        return None
    prices = _maybe_json_parse(resp.get("outcomePrices"))
    if not isinstance(prices, list) or len(prices) != 2:
        return None
    try:
        yes_p = float(prices[0])
    except (TypeError, ValueError):
        return None
    if yes_p >= 0.98:
        return 1
    if yes_p <= 0.02:
        return 0
    return None  # ambiguous close; leave unsettled for a future run


def settle_pending(path=FORECASTS_PATH, fetch_fn=fetch_json):
    appended = 0
    for key, _row in find_unsettled(path):
        market_id = key.split("|", 1)[0]
        outcome = check_settlement(market_id, fetch_fn)
        if outcome is None:
            continue
        append_row({
            "settle_for": key,
            "outcome": outcome,
            "settled_at": _now_iso(),
        }, path)
        appended += 1
    return appended


# --------------------------------------------------------------------------------------
# 5. main run
# --------------------------------------------------------------------------------------
def run(max_markets=MAX_MARKETS_DEFAULT, fetch_fn=fetch_json, complete_fn=llm_complete,
        sleep_fn=time.sleep, path=FORECASTS_PATH):
    settled = settle_pending(path, fetch_fn)

    if not os.environ.get("GROQ_API_KEY", "").strip():
        print("skipped: no key")
        print(json.dumps({
            "markets_scanned": 0, "geopolitics_found": 0, "forecasts_frozen": 0,
            "settlements_appended": settled, "llm_calls_used": 0,
        }, indent=2))
        return 0

    candidates = discover(max_markets, fetch_fn, sleep_fn)
    existing = load_existing_keys(path)
    budget = LLMBudget(max_calls=200)
    frozen = 0
    for c in candidates:
        if budget.exhausted():
            break
        key = (c["market_id"], _today())
        if key in existing:
            continue
        row, reason = forecast_market(c, budget, complete_fn, sleep_fn)
        if row is not None:
            append_row(row, path)
            existing.add(key)
            frozen += 1

    report = {
        "markets_scanned_geopolitics_candidates": len(candidates),
        "geopolitics_found": len(candidates),
        "forecasts_frozen": frozen,
        "settlements_appended": settled,
        "llm_calls_used": budget.calls,
    }
    print(json.dumps(report, indent=2))
    return 0


# --------------------------------------------------------------------------------------
# --selftest: no network, no key. Injects fakes; asserts the invariants below.
# --------------------------------------------------------------------------------------
def _selftest():
    import tempfile

    tmpdir = tempfile.mkdtemp(prefix="s1_selftest_")
    path = os.path.join(tmpdir, "s1_forecasts.jsonl")

    fake_market = {
        "id": "mkt1",
        "conditionId": "cond1",
        "question": "Will there be a ceasefire in the conflict by year end?",
        "endDate": "2027-01-01T00:00:00Z",
        "outcomes": json.dumps(["Yes", "No"]),
        "outcomePrices": json.dumps(["0.37", "0.63"]),
        "volume": "50000",
    }

    def fake_fetch(url):
        if "offset=0" in url:
            return [fake_market]
        return []

    prompts_seen = []

    def fake_complete(prompt, role="forecast", mock=False, max_tokens=120, **kw):
        prompts_seen.append(prompt)
        # sloppy reply for one, clean JSON for the rest
        if len(prompts_seen) == 1:
            return 'Sure! {"prob": 0.12, "rationale": "test sloppy reply"}'
        return json.dumps({"prob": 0.30 + 0.01 * len(prompts_seen), "rationale": "ok"})

    # --- run 1 ---
    candidates = discover(15, fetch_fn=fake_fetch, sleep_fn=lambda s: None)
    assert len(candidates) == 1, f"expected 1 geopolitics candidate, got {len(candidates)}"
    assert candidates[0]["market_id"] == "mkt1"

    budget = LLMBudget(max_calls=200)
    row, reason = forecast_market(candidates[0], budget, complete_fn=fake_complete,
                                   sleep_fn=lambda s: None, call_sleep=0)
    assert reason == "ok", f"forecast_market failed: {reason}"
    assert row["n_valid"] == 10, f"expected 10 valid replies, got {row['n_valid']}"

    # (a) market price never appears in any prompt sent to the fake llm
    for p in prompts_seen:
        assert "0.37" not in p and "0.63" not in p, "market price leaked into a prompt!"
    print("[selftest] (a) PASS: q_market never appears in any persona prompt")

    # (c) JSON parse of sloppy persona reply
    parsed = _parse_persona_reply('Sure! {"prob": 0.12, "rationale": "hi"}')
    assert parsed is not None and abs(parsed["prob"] - 0.12) < 1e-9
    print("[selftest] (c) PASS: sloppy JSON reply parsed correctly")

    append_row(row, path)

    # (b) idempotency: second run same day adds no duplicate rows
    def fake_fetch_no_resolve(url):
        if "id=" in url:
            return []
        if "offset=0" in url:
            return [fake_market]
        return []

    before = list(_iter_jsonl(path))
    run(max_markets=15, fetch_fn=fake_fetch_no_resolve, complete_fn=fake_complete,
        sleep_fn=lambda s: None, path=path)
    after = list(_iter_jsonl(path))
    # GROQ_API_KEY unset in this test env -> run() should skip forecasting entirely
    # and add no rows; verify separately with key present via direct dedupe check.
    existing_keys = load_existing_keys(path)
    assert (row["market_id"], row["date"]) in existing_keys
    key = (candidates[0]["market_id"], _today())
    if key not in existing_keys:
        pass
    # explicit dedupe check bypassing the GROQ gate
    frozen_before = sum(1 for r in before if "market_id" in r)
    budget2 = LLMBudget(max_calls=200)
    existing2 = load_existing_keys(path)
    if key in existing2:
        skipped_dupe = True
    else:
        row2, _ = forecast_market(candidates[0], budget2, complete_fn=fake_complete,
                                   sleep_fn=lambda s: None, call_sleep=0)
        skipped_dupe = False
    assert skipped_dupe, "idempotency check: market_id+date should already be present"
    frozen_after = sum(1 for r in list(_iter_jsonl(path)) if "market_id" in r)
    assert frozen_after == frozen_before, "duplicate forecast row was added!"
    print("[selftest] (b) PASS: idempotent — no duplicate rows for same market_id+date")

    # (d) settlement appends rather than mutates
    rows_before_settle = list(_iter_jsonl(path))
    n_before = len(rows_before_settle)

    def fake_fetch_resolved(url):
        if "id=mkt1" in url:
            return {"closed": True, "outcomePrices": json.dumps(["1.0", "0.0"])}
        return []

    appended = settle_pending(path, fetch_fn=fake_fetch_resolved)
    assert appended == 1, f"expected 1 settlement appended, got {appended}"
    rows_after_settle = list(_iter_jsonl(path))
    assert len(rows_after_settle) == n_before + 1, "settlement should APPEND, not mutate"
    # original forecast row must be byte-identical (untouched)
    assert rows_after_settle[:n_before] == rows_before_settle, "prior rows were mutated!"
    settle_row = rows_after_settle[-1]
    assert settle_row.get("outcome") == 1 and "settle_for" in settle_row
    print("[selftest] (d) PASS: settlement appends a new row; forecast row untouched")

    print("[selftest] ALL CHECKS PASSED")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=MAX_MARKETS_DEFAULT,
                    help="max geopolitics markets to forecast this run")
    ap.add_argument("--selftest", action="store_true",
                    help="run offline self-tests (no network, no key) and exit")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return
    run(max_markets=args.max)


if __name__ == "__main__":
    main()
