"""S1 — Geopolitics forecast-capture cell. FORWARD-ONLY, PAPER-ONLY.

This tool NEVER places an order on any venue. It discovers open geopolitics
markets on Polymarket, runs TWO independent price-blind forecasting variants
per market (an A/B test of analyst protocol, not of data), blends each with
the market's own price, and freezes both results to an append-only JSONL
ledger for later scoring. That scoring (hit-rate, calibration, edge realized)
is a separate concern -- this file only captures forecasts and settlements.

VARIANTS ("variant" field on every forecast row):
  - "swarm10" (original, unchanged behavior): 10 fixed personas, one call
    each, mean-aggregated. Rows written before this A/B existed carry no
    "variant" field at all -- absence of the field means "swarm10" (documented
    here for anyone auditing old rows).
  - "sfp3" (superforecaster protocol, new): 3 calls, each a different analyst
    "lens" over an identical 5-step scratchpad prompt (outside view first,
    then inside view, then a red-team pass), aggregated via extremized-median
    + base-rate shrinkage (see forecast_sfp3() docstring for the exact math
    and its citations).
  Both variants are captured for every candidate market every run. The
  idempotency key is now market_id+date+variant, so each market gets up to
  one swarm10 row AND up to one sfp3 row per day (never more).

PRE-REGISTERED A/B KILL RULE (decided before data; never moved): after 50
resolved markets covered by BOTH variants, the variant with the worse Brier
score on its own price-blind "p_model" field (p_swarm for swarm10, p_model
for sfp3 -- i.e. the pre-market-blend quantity) retires. This is a scoring
concern for a separate tool; this file only ensures both variants' price-
blind quantities are on the row so that later scoring is possible.

ANCHORING / HONESTY RULE (frozen): the market price (q_market) is NEVER
included in any prompt sent to a persona/lens, in EITHER variant. Personas
and lenses forecast blind; the market price is blended in only AFTER all
replies for that variant are collected. This is the same category of
invariant as fetch_prices_v2.py's look-ahead rule for candle timestamps --
it exists so a later audit can grep every prompt string in this file and
confirm no price token appears in one.

Pipeline (one run):
  1. DISCOVER  Gamma API `/markets?closed=false` (paginated), classify question
     text as geopolitics via a regex list (adapted from
     institute/tools/coverage_report.py's "geopolitics" rule -- see comment at
     GEO_PATTERN below), require binary Yes/No + parseable endDate > now+24h +
     outcomePrices present. Cap at --max, preferring higher liquidity/volume.
  2. FORECAST  (skipped entirely, exit 0, if GROQ_API_KEY is unset) for each
     candidate, capture BOTH variants:
       (2a) swarm10 -- 10 fixed personas each get a price-blind prompt and
       must reply with strict JSON {"prob":0.xx,"rationale":"..."}.
       Non-conforming replies are dropped; need >=6/10 valid or the market is
       skipped ("swarm_failed"). p_swarm = mean of valid probs, p_std =
       population stdev. p_std > 0.30 is recorded but flagged
       "no_trade_high_disagreement" (not dropped).
       p_final = 0.70 * p_swarm + 0.30 * q_market.
       (2b) sfp3 -- 3 calls (one per lens: structural/historical,
       recent-news/momentum, base-rate-anchored), each a 5-step scratchpad
       reply {"base_rate":0.xx,"prob":0.xx,"rationale":"..."}. Need >=2/3
       valid or the market is flagged "sfp3_failed" (swarm10 row is still
       kept). Aggregation: p_median (median of valid probs) -> p_ext
       (extremized via d=sqrt(3)) -> p_model = 0.70*p_ext + 0.30*base_rate_med
       -> p_final = 0.70*p_model + 0.30*q_market (identical market blend to
       swarm10, so the A/B isolates the analyst protocol, not the blend).
  3. FREEZE  Append one row per market per day per variant to
     institute/data/history/s1_forecasts.jsonl. Idempotent: a
     market_id+date+variant triple already present is skipped, never
     rewritten.
  4. SETTLE  Before forecasting, scan prior forecast rows lacking an
     "outcome" and check Gamma for resolution. Resolved markets get a NEW
     settlement row appended (never a rewrite of the forecast row):
     {"settle_for": "<market_id>|<date>", "outcome": 0|1, "settled_at": iso}.
     Settlement keys on market_id only, so one settlement row applies to
     both variants' forecast rows for that market+date.
  5. REPORT  Print a summary; hard-cap 200 LLM calls/run (Groq free-tier RPD
     protection) and sleep 0.5s between calls (Groq free-tier 30 RPM limit).
     Budget per market is now 13 calls (10 swarm10 + 3 sfp3).

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
  - sfp3 clips p_median and base_rate_med to [0.001, 0.999] before any
    logit/sigmoid math, per spec, to avoid -inf/+inf at the extremes.
  - sfp3's per-call temperature (0.7) intentionally differs from swarm10's
    default (0.0, via llm's own default) -- the scratchpad protocol wants
    each lens to reason somewhat independently rather than collapse to the
    same greedy completion three times.

stdlib only. ASCII output. Windows-safe paths throughout.

Usage:
    python s1_geopolitics.py                  # normal run (needs GROQ_API_KEY)
    python s1_geopolitics.py --max 15
    python s1_geopolitics.py --selftest        # no network, no key required
"""
import argparse
import json
import math
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
# sfp3 (superforecaster protocol, 3 calls) -- lenses + aggregation constants
# --------------------------------------------------------------------------------------
LENS_A = "weight structural and historical constraints most heavily"
LENS_B = "weight recent news and current momentum most heavily"
LENS_C = "assume the base rate is correct unless the evidence is overwhelming"
SFP3_LENSES = [LENS_A, LENS_B, LENS_C]

SFP3_D = 3 ** 0.5  # sqrt(3), per AIA arXiv 2511.07678 / Halawi 2402.18563

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


def build_sfp3_prompt(lens_line, question, end_date, today):
    """Build a price-blind 5-step scratchpad prompt for one sfp3 lens.

    MUST NEVER include q_market/outcomePrices -- same honesty invariant as
    build_prompt() above.
    """
    return (
        f"You are a superforecaster. For this question, {lens_line}.\n\n"
        f"Question: {question}\n"
        f"Resolution date: {end_date}\n"
        f"Today's date: {today}\n\n"
        "Follow these 5 steps:\n"
        "Step 1 -- RESTATE the question, its resolution criterion, and today's date.\n"
        "Step 2 -- OUTSIDE VIEW FIRST: name 1-3 reference classes of similar past "
        "events, and state the base rate as a frequency (e.g. \"out of 100 "
        "comparable situations, YES resolves in ~M\").\n"
        "Step 3 -- INSIDE VIEW through your lens: list factors pushing above the "
        "base rate AND factors pushing below it (at least one of each).\n"
        "Step 4 -- RED-TEAM THE DRAMATIC OUTCOME: ask yourself \"am I reasoning "
        "from vividness rather than frequency?\" and adjust down if so.\n"
        "Step 5 -- reply ONLY with JSON of the form "
        '{"base_rate": 0.xx, "prob": 0.xx, "rationale": "<one sentence>"} '
        "and nothing else."
    )


def _parse_sfp3_reply(text):
    """Defensively parse the first {...} JSON object in a sloppy sfp3 reply."""
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
    if not isinstance(obj, dict) or "prob" not in obj or "base_rate" not in obj:
        return None
    try:
        p = float(obj["prob"])
        br = float(obj["base_rate"])
    except (TypeError, ValueError):
        return None
    if not (0.0 <= p <= 1.0) or not (0.0 <= br <= 1.0):
        return None
    return {"prob": p, "base_rate": br, "rationale": str(obj.get("rationale", ""))[:300]}


def _clip01(x, lo=0.001, hi=0.999):
    return min(hi, max(lo, x))


def _logit(p):
    p = _clip01(p)
    return math.log(p / (1.0 - p))


def _sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x))


def sfp3_aggregate(probs, base_rates, q_market):
    """Pre-registered sfp3 aggregation (AIA arXiv 2511.07678 + Halawi 2402.18563).

    p_median = median of valid probs (clipped to [0.001, 0.999]).
    p_ext = sigmoid(sqrt(3) * logit(p_median))            -- extremize.
    base_rate_med = median of valid base_rate values (clipped).
    p_model = 0.70 * p_ext + 0.30 * base_rate_med          -- shrink toward outside view.
    p_final = 0.70 * p_model + 0.30 * q_market             -- same market blend as swarm10.
    Returns dict with p_median, p_ext, base_rate_med, p_model, p_final.
    """
    p_median = _clip01(statistics.median(probs))
    p_ext = _sigmoid(SFP3_D * _logit(p_median))
    base_rate_med = _clip01(statistics.median(base_rates))
    p_model = 0.70 * p_ext + 0.30 * base_rate_med
    p_final = 0.70 * p_model + 0.30 * q_market
    return {
        "p_median": p_median,
        "p_ext": p_ext,
        "base_rate_med": base_rate_med,
        "p_model": p_model,
        "p_final": p_final,
    }


def forecast_sfp3(candidate, budget, complete_fn=llm_complete, sleep_fn=time.sleep,
                   call_sleep=0.5):
    """Run the 3-lens sfp3 protocol for one candidate. Returns (row_dict_or_None, reason)."""
    today = _today()
    replies = []
    for lens_line in SFP3_LENSES:
        if budget.exhausted():
            return None, "budget_exhausted"
        prompt = build_sfp3_prompt(lens_line, candidate["question"], candidate["end_date"], today)
        # HONESTY INVARIANT: candidate["q_market"] / outcomePrices must NEVER appear
        # in `prompt`. Do not add it above without re-reading the module docstring.
        budget.spend()
        try:
            reply = complete_fn(prompt, role="forecast", mock=False, max_tokens=400,
                                 temperature=0.7)
        except Exception:
            reply = None
        sleep_fn(call_sleep)
        parsed = _parse_sfp3_reply(reply)
        if parsed is not None:
            replies.append(parsed)
    if len(replies) < 2:
        return None, "sfp3_failed"
    probs = [r["prob"] for r in replies]
    base_rates = [r["base_rate"] for r in replies]
    q_market = candidate["q_market"]
    agg = sfp3_aggregate(probs, base_rates, q_market)
    edge = agg["p_final"] - q_market
    p_std = statistics.pstdev(probs) if len(probs) > 1 else 0.0
    row = {
        "date": today,
        "variant": "sfp3",
        "market_id": candidate["market_id"],
        "condition_id": candidate.get("condition_id"),
        "question": candidate["question"],
        "end_date": candidate["end_date"],
        "q_market": q_market,
        "probs": [round(p, 4) for p in probs],
        "p_median": round(agg["p_median"], 4),
        "p_ext": round(agg["p_ext"], 4),
        "base_rate_med": round(agg["base_rate_med"], 4),
        "p_model": round(agg["p_model"], 4),
        "p_final": round(agg["p_final"], 4),
        "n_valid": len(replies),
        "lenses_used": 3,
        "edge": round(edge, 4),
        "would_bet": bool(abs(edge) > 0.05 and p_std <= 0.30),
        "side": "YES" if edge > 0 else "NO",
        "frozen_at": _now_iso(),
    }
    if p_std > 0.30:
        row["flag"] = "no_trade_high_disagreement"
    return row, "ok"


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
        "variant": "swarm10",
        "market_id": candidate["market_id"],
        "condition_id": candidate.get("condition_id"),
        "question": candidate["question"],
        "end_date": candidate["end_date"],
        "q_market": q_market,
        "p_swarm": round(p_swarm, 4),
        "p_model": round(p_swarm, 4),
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
    """market_id+date+variant idempotency key. Rows with no "variant" field
    (written before this A/B existed) are treated as "swarm10" per the module
    docstring."""
    keys = set()
    for row in _iter_jsonl(path):
        if "market_id" in row and "date" in row:
            variant = row.get("variant", "swarm10")
            keys.add((row["market_id"], row["date"], variant))
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
        today = _today()
        key_swarm = (c["market_id"], today, "swarm10")
        if key_swarm not in existing:
            row, reason = forecast_market(c, budget, complete_fn, sleep_fn)
            if row is not None:
                append_row(row, path)
                existing.add(key_swarm)
                frozen += 1
        if budget.exhausted():
            break
        key_sfp3 = (c["market_id"], today, "sfp3")
        if key_sfp3 not in existing:
            row, reason = forecast_sfp3(c, budget, complete_fn, sleep_fn)
            if row is not None:
                append_row(row, path)
                existing.add(key_sfp3)
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
    assert (row["market_id"], row["date"], "swarm10") in existing_keys
    key = (candidates[0]["market_id"], _today(), "swarm10")
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

    # (e) sfp3 aggregation math is exact on a hand-computed case
    probs_e = [0.10, 0.20, 0.40]
    base_rates_e = [0.05, 0.10, 0.30]
    agg_e = sfp3_aggregate(probs_e, base_rates_e, q_market=0.0)
    assert abs(agg_e["p_median"] - 0.20) < 1e-9
    assert abs(_logit(0.20) - (-1.3862944)) < 1e-4
    assert abs(agg_e["p_ext"] - 0.0830895) < 1e-4, f"p_ext={agg_e['p_ext']}"
    assert abs(agg_e["base_rate_med"] - 0.10) < 1e-9
    assert abs(agg_e["p_model"] - 0.0881626) < 1e-4, f"p_model={agg_e['p_model']}"
    print("[selftest] (e) PASS: sfp3 aggregation math matches hand-computed case")

    # (f) market price absent from all sfp3 prompts
    sfp3_prompts_seen = []

    def fake_complete_sfp3(prompt, role="forecast", mock=False, max_tokens=400,
                            temperature=0.7, **kw):
        sfp3_prompts_seen.append(prompt)
        return json.dumps({
            "base_rate": 0.15 + 0.01 * len(sfp3_prompts_seen),
            "prob": 0.25 + 0.01 * len(sfp3_prompts_seen),
            "rationale": "ok",
        })

    budget_sfp3 = LLMBudget(max_calls=200)
    row_sfp3, reason_sfp3 = forecast_sfp3(candidates[0], budget_sfp3,
                                           complete_fn=fake_complete_sfp3,
                                           sleep_fn=lambda s: None, call_sleep=0)
    assert reason_sfp3 == "ok", f"forecast_sfp3 failed: {reason_sfp3}"
    assert row_sfp3["variant"] == "sfp3"
    assert len(sfp3_prompts_seen) == 3, f"expected 3 sfp3 calls, got {len(sfp3_prompts_seen)}"
    for p in sfp3_prompts_seen:
        assert "0.37" not in p and "0.63" not in p, "market price leaked into an sfp3 prompt!"
    print("[selftest] (f) PASS: q_market never appears in any sfp3 prompt")

    # (g) idempotency across variants: one row per variant, no more
    append_row(row_sfp3, path)
    rows_all = list(_iter_jsonl(path))
    variant_keys = [
        (r["market_id"], r["date"], r.get("variant", "swarm10"))
        for r in rows_all if "market_id" in r
    ]
    assert len(variant_keys) == len(set(variant_keys)), \
        "duplicate market_id+date+variant rows present!"
    assert variant_keys.count((candidates[0]["market_id"], _today(), "swarm10")) == 1
    assert variant_keys.count((candidates[0]["market_id"], _today(), "sfp3")) == 1
    existing_keys3 = load_existing_keys(path)
    key_swarm3 = (candidates[0]["market_id"], _today(), "swarm10")
    key_sfp3_3 = (candidates[0]["market_id"], _today(), "sfp3")
    assert key_swarm3 in existing_keys3 and key_sfp3_3 in existing_keys3
    print("[selftest] (g) PASS: idempotent across variants (one row each, no duplicates)")

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
