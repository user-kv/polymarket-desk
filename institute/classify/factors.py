"""Factor loadings for the portfolio correlation model (CONSTITUTION §11 Seam 2).

Cheap, prior-based loadings assigned at classification time — correlation is
computed from SHARED loadings, never from sparse pairwise history. A1 ships the
obvious factors; the LLM-assigned version matures later.
"""


def loadings(archetype, meta=None):
    meta = meta or {}
    f = {}
    if archetype == "weather-daily":
        # markets on the same region+day share synoptics
        f["region_day"] = f"{meta.get('station', '?')}|{meta.get('date', '?')}"
        f["weather"] = 1.0
    elif archetype == "crypto-daily":
        f["crypto_beta"] = 1.0
        f["underlying"] = meta.get("symbol", "?")
    elif archetype == "sports-game":
        f["league"] = meta.get("league", "?")
        f["event"] = meta.get("event_id", "?")
    elif archetype == "econ-release":
        f["macro"] = 1.0
        f["release"] = meta.get("release", "?")
    return f
