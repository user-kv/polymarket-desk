"""Archetype tagging (rules first; LLM fallback is a later milestone).

Fast-resolving archetypes only for the initial universe (CONSTITUTION §4).
"""

_CRYPTO = ("bitcoin", "btc", "ethereum", "eth", "solana", "sol", "crypto", "dogecoin", "xrp")
_SPORTS = (" vs ", " vs. ", "defeat", "beat the", "win the game", "match", "nba", "nfl",
           "mlb", "premier league", "ufc", "soccer")
_ECON = ("cpi", "inflation", "fed ", "interest rate", "rate cut", "rate hike", "jobs report",
         "gdp", "unemployment", "nonfarm", "fomc")


def classify(question, slug=""):
    s = (str(question) + " " + str(slug)).lower()
    if "highest temperature" in s or "temperature in" in s:
        return "weather-daily"
    if any(k in s for k in _CRYPTO):
        return "crypto-daily"
    if any(k in s for k in _ECON):
        return "econ-release"
    if any(k in s for k in _SPORTS):
        return "sports-game"
    return "other"


FAST_RESOLVING = {"weather-daily", "crypto-daily", "sports-game", "econ-release"}


def in_initial_universe(archetype):
    return archetype in FAST_RESOLVING
