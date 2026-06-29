"""Sports archetype baselines + feature seam (ARCHITECTURE §5 archetype #2).

No live sports resolved-data sensor yet, so these operate on the same
ResolvedMarket shape and read sharp external signals from `meta`. The edge
claim: a sharper external market (sportsbook line) or a power-rating model
carries information the thin Polymarket price has not yet absorbed.
"""

# minimum disagreement before we fade the PM price (avoid trading noise)
_ODDS_THRESH = 0.03
_MODEL_THRESH = 0.05


def odds_follow(rm, thresh=_ODDS_THRESH, **kw):
    """Bet toward a sharp sportsbook implied prob when it disagrees with PM.

    meta['book_prob'] = bookmaker-implied P(YES). Side YES if the book is
    materially higher than the PM price, NO if materially lower, else no bet.
    """
    book = rm.get("meta", {}).get("book_prob")
    if book is None:
        return rm["q_yes"], None
    q = rm["q_yes"]
    if book > q + thresh:
        return book, "YES"
    if book < q - thresh:
        return book, "NO"
    return book, None


def power_rating_fade(rm, thresh=_MODEL_THRESH, **kw):
    """Fade the crowd toward a power-rating model's probability.

    meta['model_prob'] = model P(YES). Same disagreement logic, wider band
    (models are noisier than sharp books).
    """
    model = rm.get("meta", {}).get("model_prob")
    if model is None:
        return rm["q_yes"], None
    q = rm["q_yes"]
    if model > q + thresh:
        return model, "YES"
    if model < q - thresh:
        return model, "NO"
    return model, None


SPORTS_BASELINES = {
    "odds_follow": odds_follow,
    "power_rating_fade": power_rating_fade,
}
