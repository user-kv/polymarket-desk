"""S2 -- FDA/science-approval forecast-capture cell. FORWARD-ONLY, PAPER-ONLY.

Sibling of s1_geopolitics.py: same honesty invariants (market price NEVER in
prompts; append-only; idempotent by market_id+date+variant; settlement rows
appended, never mutated; 200 LLM-call cap; 0.5s sleep between calls; exits 0
with "skipped: no key" if GROQ_API_KEY unset). Structure and helpers below
are copied (not imported) from s1_geopolitics.py per task instructions --
this file is intentionally import-free of s1.

DIFFERENCES from s1_geopolitics.py:
  1. DISCOVERY: classifies FDA/biotech/science-approval markets instead of
     geopolitics. See FDA_PATTERN / _has_med_context below -- a question must
     match an approval-shaped pattern AND carry a medical/biotech context
     token, to keep "Will Congress approve the budget?" and similar false
     positives out.
  2. VARIANT: only "sfp3" is run (no swarm10). Rows carry "variant":"sfp3"
     and "cell":"fda". build_sfp3_prompt/SFP3_LENSES/sfp3_aggregate are
     copied byte-for-byte from s1 (same math, same lenses).
  3. The sfp3 prompt's Step 2 (outside view) is FDA-flavored: it nudges the
     analyst to consider domain reference classes (overall PDUFA approval
     rate, post-ADCOM-positive approval rate) by NAME only -- no specific
     number is injected by this tool. The model must state its own figure.
  4. STORAGE: institute/data/history/fda_forecasts.jsonl (same row schema as
     s1's sfp3 rows, plus "cell": "fda").
  5. Pre-registration (decided before data; never moved):
     Success metric: after 20 resolved FDA markets, price-blind p_model
     Brier < market Brier AND net virtual ROI > 0.
     Kill: 20 resolved, ROI < 0 -> retire (PLAN/01 kill kept).
  6. --selftest covers: price-leak check, idempotency, sfp3 aggregation math
     (reuses s1's known-good hand-computed case), and the FDA-pattern
     classifier's true/false positive behavior (e.g. "Will the FDA approve
     Drug X?" -> True; "Will Congress approve the budget?" -> False).

ANCHORING / HONESTY RULE (frozen): the market price (q_market) is NEVER
included in any prompt sent to a lens. Lenses forecast blind; the market
price is blended in only AFTER all replies are collected. Same invariant
category as s1_geopolitics.py and fetch_prices_v2.py's look-ahead rule --
grep every prompt string in this file to confirm no price token appears.

Pipeline (one run):
  1. DISCOVER  Gamma API `/markets?closed=false` (paginated), classify
     question text as FDA/biotech via FDA_PATTERN + _has_med_context,
     require binary Yes/No + parseable endDate > now+24h + outcomePrices
     present. Cap at --max (default 10), preferring higher liquidity/volume.
  2. FORECAST  (skipped entirely, exit 0, if GROQ_API_KEY is unset) for each
     candidate, run the 3-lens sfp3 protocol only. Need >=2/3 valid replies
     or the market is skipped ("sfp3_failed"). Aggregation: p_median ->
     p_ext (extremized via d=sqrt(3)) -> p_model = 0.70*p_ext +
     0.30*base_rate_med -> p_final = 0.70*p_model + 0.30*q_market.
  3. FREEZE  Append one row per market per day to
     institute/data/history/fda_forecasts.jsonl. Idempotent: a
     market_id+date+variant("sfp3") triple already present is skipped,
     never rewritten.
  4. SETTLE  Before forecasting, scan prior forecast rows lacking an
     "outcome" and check Gamma for resolution. Resolved markets get a NEW
     settlement row appended (never a rewrite of the forecast row):
     {"settle_for": "<market_id>|<date>", "outcome": 0|1, "settled_at": iso}.
  5. REPORT  Print a summary; hard-cap 200 LLM calls/run (Groq free-tier RPD
     protection) and sleep 0.5s between calls (Groq free-tier 30 RPM
     limit). Budget per market is 3 calls (sfp3 only).

Spec-silent decisions (documented here per task instructions, mirroring
s1's own "Spec-silent decisions" section):
  - "highest liquidity/volume" ranking uses Gamma's `volume` field (falls
    back to `liquidity`, then 0), same as s1.
  - The double-parse quirk (outcomes/outcomePrices/clobTokenIds ship as
    JSON strings) is handled by `_maybe_json_parse`, copied verbatim from
    s1 / institute lib/polymarket.py.
  - Settlement resolution check uses Gamma `?id=` lookup, same as s1: a
    market is "resolved" when `closed` is true AND outcomePrices show a
    clean 0/1 split (tolerance 0.02); ambiguous closes are left unsettled.
  - FDA_PATTERN + _has_med_context is a two-token AND: an "approval-shaped"
    regex (FDA|approval|approve|PDUFA|advisory committee|ADCOM|biologic|
    clinical trial|phase (2|3|III)|EUA|vaccine.*approv|CDC|EMA) must be
    present, AND at least one of a medical-context token (drug|vaccine|
    trial|fda|biotech|medicine|therapy|treatment|clinical) must also be
    present, unless the approval-shaped match itself is unambiguously
    medical (FDA, PDUFA, ADCOM, EUA, biologic, CDC, EMA are exempted from
    needing a second token since they cannot plausibly appear in a non-
    medical market question). This keeps "Will the Senate approve the
    nominee?" and "Will FDA... " (crypto ticker collisions, none observed
    but plausible) out while keeping "Will the FDA approve Drug X by
    PDUFA date?" in.
  - sfp3 clips p_median and base_rate_med to [0.001, 0.999] before any
    logit/sigmoid math, identical to s1.
  - sfp3's per-call temperature (0.7) matches s1's sfp3 temperature.

stdlib only. ASCII output. Windows-safe paths throughout.

Usage:
    python s2_fda.py                  # normal run (needs GROQ_API_KEY)
    python s2_fda.py --max 10
    python s2_fda.py --selftest        # no network, no key required
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
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
# institute/FABLE5/out/tools -> up 3 -> institute
INSTITUTE_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if INSTITUTE_ROOT not in sys.path:
    sys.path.insert(0, INSTITUTE_ROOT)

from agents.llm import complete as llm_complete  # noqa: E402

DATA = os.path.join(INSTITUTE_ROOT, "data", "history")
FORECASTS_PATH = os.path.join(DATA, "fda_forecasts.jsonl")

GAMMA_MARKETS = "https://gamma-api.polymarket.com/markets"
UA = {"User-Agent": "institute-s2-fda/1.0", "Accept": "application/json"}

MAX_MARKETS_DEFAULT = 10
DISCOVER_PAGE = 100
DISCOVER_MAX_OFFSET = 500  # paginate up to ~500 markets scanned
MIN_LEAD_SECONDS = 24 * 3600

# --------------------------------------------------------------------------------------
# sfp3 (superforecaster protocol, 3 calls) -- lenses + aggregation constants.
# Copied verbatim from s1_geopolitics.py -- same math, same lenses.
# --------------------------------------------------------------------------------------
LENS_A = "weight structural and historical constraints most heavily"
LENS_B = "weight recent news and current momentum most heavily"
LENS_C = "assume the base rate is correct unless the evidence is overwhelming"
SFP3_LENSES = [LENS_A, LENS_B, LENS_C]

SFP3_D = 3 ** 0.5  # sqrt(3), per AIA arXiv 2511.07678 / Halawi 2402.18563

# --------------------------------------------------------------------------------------
# FDA / science-approval classifier.
#
# FDA_PATTERN matches "approval-shaped" question text. A subset of its
# alternatives (fda, pdufa, adcom, eua, biologic, cdc, ema) are unambiguously
# medical/regulatory and exempted from needing a second context token (see
# UNAMBIGUOUS_TOKENS below); the rest (approval|approve.*drug|advisory
# committee|clinical trial|phase (2|3|III)|vaccine.*approv) must co-occur
# with a medical-context token via _has_med_context to avoid sports/crypto/
# politics false positives such as "Will Congress approve the budget?".
# --------------------------------------------------------------------------------------
FDA_PATTERN = re.compile(
    r"\bfda\b|\bapproval\b|approve.*drug|\bpdufa\b|advisory committee|\badcom\b|"
    r"\bbiologic\b|clinical trial|phase\s*(2|3|iii)\b|\beua\b|vaccine.*approv|"
    r"\bcdc\b|\bema\b",
    re.IGNORECASE,
)

# Alternatives above that are unambiguously medical/regulatory on their own
# (cannot plausibly appear in a non-medical market question), so a bare match
# on one of these needs no second context token.
UNAMBIGUOUS_TOKENS = re.compile(
    r"\bfda\b|\bpdufa\b|\badcom\b|\beua\b|\bbiologic\b|\bcdc\b|\bema\b",
    re.IGNORECASE,
)

MED_CONTEXT_PATTERN = re.compile(
    r"\bdrug\b|\bvaccine\b|\btrial\b|\bbiotech\b|\bmedicine\b|\btherapy\b|"
    r"\btreatment\b|\bclinical\b|\bpharma\b|\bdisease\b",
    re.IGNORECASE,
)


def _has_med_context(question):
    return bool(MED_CONTEXT_PATTERN.search(question or ""))


def is_fda(question):
    """True if question is an FDA/biotech/science-approval market.

    Requires FDA_PATTERN to match. If the matched alternative is one of the
    unambiguous tokens (fda/pdufa/adcom/eua/biologic/cdc/ema), that alone is
    sufficient. Otherwise (approval|approve.*drug|advisory committee|
    clinical trial|phase N|vaccine.*approv) a second, independent medical-
    context token must also be present in the question.
    """
    q = question or ""
    if not FDA_PATTERN.search(q):
        return False
    if UNAMBIGUOUS_TOKENS.search(q):
        return True
    return _has_med_context(q)


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
SEARCH_TERMS = ["FDA", "PDUFA", "vaccine", "drug", "clinical trial", "biotech",
                "CDC", "EMA approval"]


def discover(max_markets, fetch_fn=fetch_json, sleep_fn=time.sleep):
    """Search Gamma per term, classify, filter, return up to max_markets candidates.

    Uses /public-search instead of /markets offset-paging: Gamma's offset hard-caps
    at ~2100 open markets ordered away from the science long tail — a 2026-07-06
    live probe found ZERO FDA markets via paging but 38 via search.
    """
    now = time.time()
    candidates = []
    seen_ids = set()
    for term in SEARCH_TERMS:
        url = (f"https://gamma-api.polymarket.com/public-search?"
               f"q={urllib.parse.quote(term)}&limit_per_type=20")
        try:
            d = fetch_fn(url)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError):
            continue
        batch = [m for e in (d.get("events") or []) for m in (e.get("markets") or [])
                 if not m.get("closed")]
        sleep_fn(0.1)
        for m in batch:
            if str(m.get("id")) in seen_ids:
                continue
            seen_ids.add(str(m.get("id")))
            question = m.get("question")
            if not is_fda(question):
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
    candidates.sort(key=lambda c: -c["volume"])
    return candidates[:max_markets]


# --------------------------------------------------------------------------------------
# 2. FORECAST (sfp3 only)
# --------------------------------------------------------------------------------------
def build_sfp3_prompt(lens_line, question, end_date, today):
    """Build a price-blind 5-step scratchpad prompt for one sfp3 lens.

    FDA-flavored Step 2: nudges the analyst toward domain reference classes
    (overall PDUFA approval rate, post-ADCOM-positive approval rate) BY NAME
    only -- this tool never injects a specific number; the model must state
    its own base rate.

    MUST NEVER include q_market/outcomePrices -- same honesty invariant as
    s1_geopolitics.py's build_prompt()/build_sfp3_prompt().
    """
    return (
        f"You are a superforecaster. For this question, {lens_line}.\n\n"
        f"Question: {question}\n"
        f"Resolution date: {end_date}\n"
        f"Today's date: {today}\n\n"
        "Follow these 5 steps:\n"
        "Step 1 -- RESTATE the question, its resolution criterion, and today's date.\n"
        "Step 2 -- OUTSIDE VIEW FIRST: name 1-3 reference classes of similar past "
        "regulatory decisions. If this concerns an FDA or comparable regulatory "
        "decision, consider relevant reference classes such as the overall "
        "historical PDUFA approval rate and the historical approval rate "
        "following a positive advisory-committee (ADCOM) vote -- state your own "
        "estimate of the applicable base rate as a frequency (e.g. \"out of 100 "
        "comparable situations, YES resolves in ~M\"); do not assume any specific "
        "figure was given to you.\n"
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

    Identical math to s1_geopolitics.py's sfp3_aggregate():
    p_median = median of valid probs (clipped to [0.001, 0.999]).
    p_ext = sigmoid(sqrt(3) * logit(p_median))            -- extremize.
    base_rate_med = median of valid base_rate values (clipped).
    p_model = 0.70 * p_ext + 0.30 * base_rate_med          -- shrink toward outside view.
    p_final = 0.70 * p_model + 0.30 * q_market             -- market blend.
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


class LLMBudget:
    """Tracks call count across a run; hard-caps at max_calls."""

    def __init__(self, max_calls=200):
        self.max_calls = max_calls
        self.calls = 0

    def exhausted(self):
        return self.calls >= self.max_calls

    def spend(self):
        self.calls += 1


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
        "cell": "fda",
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


# --------------------------------------------------------------------------------------
# 3. FREEZE (append-only, idempotent by market_id+date+variant)
# --------------------------------------------------------------------------------------
def load_existing_keys(path=FORECASTS_PATH):
    """market_id+date+variant idempotency key (variant is always "sfp3" in this cell)."""
    keys = set()
    for row in _iter_jsonl(path):
        if "market_id" in row and "date" in row:
            variant = row.get("variant", "sfp3")
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
            "markets_scanned": 0, "fda_found": 0, "forecasts_frozen": 0,
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
        key_sfp3 = (c["market_id"], today, "sfp3")
        if key_sfp3 not in existing:
            row, reason = forecast_sfp3(c, budget, complete_fn, sleep_fn)
            if row is not None:
                append_row(row, path)
                existing.add(key_sfp3)
                frozen += 1

    report = {
        "markets_scanned_fda_candidates": len(candidates),
        "fda_found": len(candidates),
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

    tmpdir = tempfile.mkdtemp(prefix="s2_selftest_")
    path = os.path.join(tmpdir, "fda_forecasts.jsonl")

    # (h) FDA-pattern classifier true/false positives
    assert is_fda("Will the FDA approve Drug X by the PDUFA date?") is True
    assert is_fda("Will Congress approve the budget?") is False
    assert is_fda("Will the Senate approve the nominee?") is False
    assert is_fda("Will the FDA grant EUA for the new vaccine this year?") is True
    assert is_fda("Will the advisory committee vote positively on the new cancer "
                  "drug's clinical trial results?") is True
    assert is_fda("Will Manchester United win the FA Cup?") is False
    assert is_fda("Will the team's phase 3 project ship on time?") is False
    print("[selftest] (h) PASS: FDA-pattern classifier true/false positives correct")

    fake_market = {
        "id": "mkt_fda1",
        "conditionId": "cond_fda1",
        "question": "Will the FDA approve the new Alzheimer's drug by its PDUFA date?",
        "endDate": "2027-01-01T00:00:00Z",
        "outcomes": json.dumps(["Yes", "No"]),
        "outcomePrices": json.dumps(["0.42", "0.58"]),
        "volume": "20000",
    }

    def fake_fetch(url):
        # public-search shape: one term returns the market, the rest return empty
        if "q=FDA" in url:
            return {"events": [{"markets": [fake_market]}]}
        return {"events": []}

    # --- discover ---
    candidates = discover(10, fetch_fn=fake_fetch, sleep_fn=lambda s: None)
    assert len(candidates) == 1, f"expected 1 fda candidate, got {len(candidates)}"
    assert candidates[0]["market_id"] == "mkt_fda1"

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

    budget = LLMBudget(max_calls=200)
    row, reason = forecast_sfp3(candidates[0], budget, complete_fn=fake_complete_sfp3,
                                 sleep_fn=lambda s: None, call_sleep=0)
    assert reason == "ok", f"forecast_sfp3 failed: {reason}"
    assert row["variant"] == "sfp3" and row["cell"] == "fda"
    assert len(sfp3_prompts_seen) == 3, f"expected 3 sfp3 calls, got {len(sfp3_prompts_seen)}"
    for p in sfp3_prompts_seen:
        assert "0.42" not in p and "0.58" not in p, "market price leaked into an sfp3 prompt!"
    print("[selftest] (a) PASS: q_market never appears in any sfp3 prompt")

    # (c) sloppy JSON parse
    parsed = _parse_sfp3_reply('Sure! {"base_rate": 0.10, "prob": 0.12, "rationale": "hi"}')
    assert parsed is not None and abs(parsed["prob"] - 0.12) < 1e-9
    print("[selftest] (c) PASS: sloppy JSON reply parsed correctly")

    append_row(row, path)

    # (b) idempotency: dedupe check bypassing the GROQ gate
    existing = load_existing_keys(path)
    key = (candidates[0]["market_id"], _today(), "sfp3")
    assert key in existing, "expected key present after first freeze"
    frozen_before = sum(1 for r in list(_iter_jsonl(path)) if "market_id" in r)
    budget2 = LLMBudget(max_calls=200)
    if key in existing:
        skipped_dupe = True
    else:
        row2, _ = forecast_sfp3(candidates[0], budget2, complete_fn=fake_complete_sfp3,
                                 sleep_fn=lambda s: None, call_sleep=0)
        skipped_dupe = False
    assert skipped_dupe, "idempotency check: market_id+date+variant should already be present"
    frozen_after = sum(1 for r in list(_iter_jsonl(path)) if "market_id" in r)
    assert frozen_after == frozen_before, "duplicate forecast row was added!"
    print("[selftest] (b) PASS: idempotent -- no duplicate rows for same market_id+date+variant")

    # (d) settlement appends rather than mutates
    rows_before_settle = list(_iter_jsonl(path))
    n_before = len(rows_before_settle)

    def fake_fetch_resolved(url):
        if "id=mkt_fda1" in url:
            return {"closed": True, "outcomePrices": json.dumps(["1.0", "0.0"])}
        return []

    appended = settle_pending(path, fetch_fn=fake_fetch_resolved)
    assert appended == 1, f"expected 1 settlement appended, got {appended}"
    rows_after_settle = list(_iter_jsonl(path))
    assert len(rows_after_settle) == n_before + 1, "settlement should APPEND, not mutate"
    assert rows_after_settle[:n_before] == rows_before_settle, "prior rows were mutated!"
    settle_row = rows_after_settle[-1]
    assert settle_row.get("outcome") == 1 and "settle_for" in settle_row
    print("[selftest] (d) PASS: settlement appends a new row; forecast row untouched")

    # (e) sfp3 aggregation math -- reuse s1's known-good hand-computed case
    probs_e = [0.10, 0.20, 0.40]
    base_rates_e = [0.05, 0.10, 0.30]
    agg_e = sfp3_aggregate(probs_e, base_rates_e, q_market=0.0)
    assert abs(agg_e["p_median"] - 0.20) < 1e-9
    assert abs(_logit(0.20) - (-1.3862944)) < 1e-4
    assert abs(agg_e["p_ext"] - 0.0830895) < 1e-4, f"p_ext={agg_e['p_ext']}"
    assert abs(agg_e["base_rate_med"] - 0.10) < 1e-9
    assert abs(agg_e["p_model"] - 0.0881626) < 1e-4, f"p_model={agg_e['p_model']}"
    print("[selftest] (e) PASS: sfp3 aggregation math matches hand-computed case")

    # (g) idempotency: exactly one row for this market_id+date+variant
    rows_all = list(_iter_jsonl(path))
    variant_keys = [
        (r["market_id"], r["date"], r.get("variant", "sfp3"))
        for r in rows_all if "market_id" in r
    ]
    assert len(variant_keys) == len(set(variant_keys)), \
        "duplicate market_id+date+variant rows present!"
    assert variant_keys.count((candidates[0]["market_id"], _today(), "sfp3")) == 1
    print("[selftest] (g) PASS: idempotent -- one sfp3 row, no duplicates")

    print("[selftest] ALL CHECKS PASSED")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=MAX_MARKETS_DEFAULT,
                    help="max FDA/biotech markets to forecast this run")
    ap.add_argument("--selftest", action="store_true",
                    help="run offline self-tests (no network, no key) and exit")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return
    run(max_markets=args.max)


if __name__ == "__main__":
    main()
