"""Alpha Engine: swarm forecast -> reconcile -> blend -> final p (A6).

Fan-out / Fan-in pattern.  Each persona forecasts INDEPENDENTLY (no shared
state, no cross-talk) then a lightweight supervisor aggregates.

Point-in-time honesty: ``q_yes`` is the only market signal visible here.
``y`` is never in scope; it does not exist yet when a market is OPEN.
"""
import hashlib
import math
import re

from institute.scoring import clip
from institute.agents import llm
from institute.alpha.personas import PERSONAS


# ── internal helpers ──────────────────────────────────────────────────────────


def _parse_prob(text):
    """Extract the first parseable probability from LLM text.

    Accepts:
    - bare decimal  0.73 / .73 / 0.0 – 1.0
    - integer percent  73%

    Returns float in (0, 1) clipped, or None if nothing parseable.
    """
    if not text:
        return None
    # Try decimal first: match "0.73", ".42", "1.0", "0.0" etc.
    m = re.search(r"(?<!\d)(0?\.\d+|1\.0*|0\.0*)\b", text)
    if m:
        try:
            val = float(m.group(1))
            if 0.0 <= val <= 1.0:
                return clip(val)
        except ValueError:
            pass
    # Try integer percent
    m = re.search(r"\b(\d{1,3})%", text)
    if m:
        try:
            pct = int(m.group(1))
            if 0 <= pct <= 100:
                return clip(pct / 100.0)
        except ValueError:
            pass
    return None


def _mock_p(persona, market):
    """Deterministic, network-free pseudo-forecast for a persona+market pair.

    Anchors on the market prior q_yes, spreads the ensemble via a sha256
    hash (persona_id + ":" + market_id) so the jitter is reproducible and
    cannot peek at y (which isn't in scope anyway on an open market).
    """
    q = clip(market["q_yes"])
    market_id = str(market.get("market_id", ""))
    key = (persona["id"] + ":" + market_id).encode()
    h_int = int(hashlib.sha256(key).hexdigest(), 16)
    h = (h_int % 1000) / 1000.0          # deterministic [0, 1)
    jitter = (h - 0.5) * 0.10            # +/- 0.05
    return clip(q + persona["lean"] + jitter)


# ── public API ────────────────────────────────────────────────────────────────


def swarm_forecast(market, personas=None, _complete=llm.complete, mock=True):
    """Run each persona INDEPENDENTLY and return one forecast per persona.

    Returns list[dict]  each:  {"persona": id, "p": float}

    mock=True (default, all tests): deterministic, no network.
    mock=False: calls ``_complete`` with role="forecast"; falls back to the
    deterministic mock value on parse failure (never raise, never skip a persona).
    """
    if personas is None:
        personas = PERSONAS

    results = []
    for persona in personas:
        if mock:
            p = _mock_p(persona, market)
        else:
            prompt = (
                f"{persona['prompt']}\n\n"
                f"Market: {market.get('question', '')}\n"
                f"Current market probability (q_yes): {market.get('q_yes', 0.5)}\n"
                f"Additional context: {market.get('meta', {})}\n\n"
                "Reply with a single probability between 0 and 1 (e.g. 0.73)."
            )
            try:
                reply = _complete(prompt, role="forecast", mock=False)
                parsed = _parse_prob(reply)
                if parsed is None:
                    # Parse failure: fall back to deterministic mock (never skip)
                    p = _mock_p(persona, market)
                else:
                    p = parsed
            except Exception:
                p = _mock_p(persona, market)

        results.append({"persona": persona["id"], "p": p})

    return results


def reconcile(forecasts, market, _complete=llm.complete, mock=True):
    """Aggregate per-persona forecasts into p_model.

    Returns dict:  {"p_model": float, "p_std": float, "n": int}

    Research finding: naive LLM-judge aggregation is WORSE than the mean
    (overweights outliers + cascades sycophancy).  The supervisor may only
    deviate on HARD evidence; otherwise the mean stands.

    mock=True: p_model = simple mean (no LLM call).
    mock=False: Opus supervisor call; kept if parse succeeds AND diverges by
    more than 0.03 from the mean — otherwise the mean wins.
    """
    if not forecasts:
        return {"p_model": 0.5, "p_std": 0.0, "n": 0}

    ps = [f["p"] for f in forecasts]
    n = len(ps)
    mean = sum(ps) / n
    variance = sum((p - mean) ** 2 for p in ps) / n
    std = math.sqrt(variance)

    if mock:
        p_model = mean
    else:
        # Supervisor call — ask Opus to reconcile ONLY with hard evidence
        summary = (
            f"Market: {market.get('question', '')}\n"
            f"Ensemble forecasts: {[round(p, 3) for p in ps]}\n"
            f"Mean: {round(mean, 3)}  Std: {round(std, 3)}\n\n"
            "You are a supervisor.  Output a single revised probability ONLY if you "
            "can cite a concrete resolving fact that the ensemble missed.  "
            "Otherwise output the mean exactly.  Reply: one float in [0,1]."
        )
        try:
            reply = _complete(summary, role="supervise", mock=False)
            parsed = _parse_prob(reply)
            if parsed is not None and abs(parsed - mean) > 0.03:
                p_model = parsed
            else:
                p_model = mean
        except Exception:
            p_model = mean

    return {"p_model": clip(p_model), "p_std": round(std, 4), "n": n}


def blend(p_model, q_market, w=0.70):
    """Blend the model prior with the market price.

    p_final = w * p_model + (1 - w) * q_market

    w=0.70 is the PolySwarm prior: independent analysis dominates, market
    informs.  Per-archetype learned w is a LATER milestone.
    """
    return clip(w * clip(p_model) + (1.0 - w) * clip(q_market))


def forecast_market(market, w=0.70, personas=None, _complete=llm.complete, mock=True):
    """Full per-market forecast pass.

    Returns dict:
        {"p_model": float, "p_std": float, "p_final": float,
         "n_agents": int, "w": float}

    Calibration is applied LATER in forecast_store (only when n >= 200);
    this function is calibration-free by design.
    """
    if personas is None:
        personas = PERSONAS

    raw = swarm_forecast(market, personas=personas, _complete=_complete, mock=mock)
    rec = reconcile(raw, market, _complete=_complete, mock=mock)

    p_final = blend(rec["p_model"], market["q_yes"], w=w)

    return {
        "p_model": rec["p_model"],
        "p_std": rec["p_std"],
        "p_final": p_final,
        "n_agents": rec["n"],
        "w": w,
    }
