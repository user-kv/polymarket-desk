"""
lib/brain.py — LLM sizing brain for the weather paper-trader (M3).

The deterministic engine (lib/engine.py) is the hard entry gate: no bet is
placed unless ALL discipline rules pass. The brain's only jobs are:
  1. Set the Kelly SIZE MULTIPLIER (0.5 – 2.0x the base Kelly stake).
  2. VETO a bet (multiplier = 0.0) when the physical weather story or a
     known uncertainty makes the forecast unreliable in a way the rules can't.

The brain may NEVER invent a bet. It only acts on bets that already passed the
engine — a veto just suppresses one; a size-up allocates more to it.

Backend: Gemini Flash (free, GEMINI_API_KEY in env). Falls back to mock
(multiplier=1.0, no veto) when the key is absent or the API fails.

Configuration (config.json):
  "use_brain": false    — set true to enable; false = pass-through (multiplier=1.0)
  "brain_tier": "cheap" — "cheap" (Flash-Lite) for speed, "deep" for conviction
"""

from __future__ import annotations
import os
import json
import logging
import urllib.request

logger = logging.getLogger("brain")

_GEMINI_MODELS = [
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-2.5-flash",
    "gemini-flash-lite-latest",
]

_SYSTEM = """You are the sizing brain for a weather paper-trading bot (FAKE MONEY ONLY).
The deterministic engine has already verified this bet passes all entry rules.
Your ONLY job: set a Kelly size multiplier (0.5–2.0) or VETO the bet (multiplier=0.0).

VETO when:
- A known severe weather event (hurricane, ice storm) makes ensemble spread unreliable.
- The forecast direction contradicts the physical weather pattern (e.g. cold front arriving day-of).
- Thin liquidity / extreme bucket (> 10°F from mean) makes adverse selection likely.

SIZE UP (1.5–2.0) when:
- All models agree tightly AND the bucket is >= 5°F from the ensemble mean.
- The ask price is far below the ensemble probability (market clearly wrong).

SIZE DOWN (0.5–0.9) when:
- Models barely agree (diff close to the 1.5°C threshold).
- The bucket is adjacent to the mean (near-edge of the buffer zone).
- Season or city is known for rapid forecast bust (e.g. Miami summer, SF marine layer).

DEFAULT (1.0) when uncertain — do not fabricate meteorological justifications.

Respond with strict JSON only:
{"multiplier": <float 0.0–2.0>, "rationale": "<max 80 chars>", "vetoed": <bool>}"""


def _gemini_call(prompt: str) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    payload = {
        "system_instruction": {"parts": [{"text": _SYSTEM}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "maxOutputTokens": 256},
    }

    last_err = None
    for model in _GEMINI_MODELS:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={api_key}"
        )
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
        except Exception as e:
            last_err = e
            continue

    raise last_err or RuntimeError("All Gemini models failed")


def _build_prompt(market: dict, forecast: dict, evaluation: dict) -> str:
    city = market.get("city", "")
    question = market.get("question", "")
    bucket_lo = market.get("bucket_low_f")
    bucket_hi = market.get("bucket_high_f")
    ensemble_prob = evaluation.get("ensemble_prob", 0.0)
    ask = evaluation.get("ask_price", 0.0)
    edge_pct = evaluation.get("edge_pct", 0.0)
    gfs_mean = evaluation.get("gfs_mean_f", 0.0)
    ecmwf_mean = evaluation.get("ecmwf_mean_f", 0.0)
    combined_mean = evaluation.get("combined_mean_f", 0.0)
    n_members = evaluation.get("n_members", 0)
    model_weights = forecast.get("model_weights", {})

    bucket_str = (
        f"≤{bucket_hi}°F" if bucket_lo == -999.0 else
        f"≥{bucket_lo}°F" if bucket_hi == 999.0 else
        f"{bucket_lo}–{bucket_hi}°F"
    )
    weights_str = (", ".join(f"{k}={v:.2f}" for k, v in sorted(model_weights.items()))
                   if model_weights else "equal-weight (no RMSE data yet)")

    return (
        f"City: {city}\n"
        f"Market: {question}\n"
        f"Bucket: {bucket_str}  |  Ensemble mean: {combined_mean:.1f}°F\n"
        f"GFS mean: {gfs_mean:.1f}°F  |  ECMWF mean: {ecmwf_mean:.1f}°F\n"
        f"Ensemble prob: {ensemble_prob:.1%}  |  Market ask: {ask:.3f}  |  Edge: {edge_pct:.1f}pt\n"
        f"Members: {n_members}  |  Model weights: {weights_str}\n"
        f"\nShould I size up, size down, use default (1.0), or VETO this bet?"
    )


def evaluate_bet(market: dict, forecast: dict, evaluation: dict, cfg: dict) -> dict:
    """
    Ask the brain to set a Kelly multiplier for a bet that already passed the engine.

    Returns:
        multiplier (float): 0.0 = vetoed; 0.5–2.0 = scale the Kelly stake by this.
        rationale (str): one-line explanation from the brain.
        vetoed (bool): True if multiplier == 0.0.
        backend (str): "gemini" | "mock"
    """
    if not cfg.get("use_brain", False):
        return {"multiplier": 1.0, "rationale": "brain disabled", "vetoed": False, "backend": "off"}

    prompt = _build_prompt(market, forecast, evaluation)

    try:
        result = _gemini_call(prompt)
        mult = float(result.get("multiplier", 1.0))
        mult = max(0.0, min(2.0, mult))
        vetoed = bool(result.get("vetoed", False)) or mult == 0.0
        if vetoed:
            mult = 0.0
        return {
            "multiplier": mult,
            "rationale": str(result.get("rationale", ""))[:120],
            "vetoed": vetoed,
            "backend": "gemini",
        }
    except Exception as e:
        logger.warning(f"Brain call failed (non-fatal, using multiplier=1.0): {e}")
        return {"multiplier": 1.0, "rationale": f"brain unavailable: {str(e)[:60]}", "vetoed": False, "backend": "mock"}
