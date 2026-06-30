"""Market question -> structured CPI MoM claim (B1).

Conservative: returns None for anything ambiguous (UK, China, GDP, YoY annual).
Only parses US CPI MoM markets explicitly referencing a specific month.
"""
import re
import datetime

# Map month names -> 1-based int
MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}

# Abbreviations
MONTHS_ABBREV = {k[:3]: v for k, v in MONTHS.items()}
MONTHS_ABBREV["sept"] = 9  # common variant


def _month_num(token):
    """Resolve a month name (full or 3-char abbrev) to 1-based int or None."""
    t = token.lower().strip(".,")
    return MONTHS.get(t) or MONTHS_ABBREV.get(t[:3])


def _is_non_us_cpi(question):
    """Return True if the question is clearly about a non-US indicator."""
    q = question.lower()
    non_us = [
        "uk", "u.k.", "united kingdom", "britain", "british",
        "china", "chinese", "euro", "eurozone", "europe",
        "canada", "japan", "australia", "india",
        "gdp", "gross domestic",
        "year-over-year", "yoy", "annual", "y/y",
        "pce", "producer price", "ppi",
    ]
    for term in non_us:
        if term in q:
            return True
    return False


def _parse_period(question, slug):
    """Extract YYYY-MM period string from question or slug.

    Tries:
    1. Month name in question text (e.g. "in June")
    2. Month name in slug
    3. Returns None if neither found.

    Uses current year for mapping if no explicit year found.
    """
    text = question + " " + slug
    # Try to find explicit year e.g. "June 2026" or "2026 June"
    m_year = re.search(
        r"(january|february|march|april|may|june|july|august|"
        r"september|october|november|december)\s+(\d{4})",
        text, re.IGNORECASE
    )
    if m_year:
        month = _month_num(m_year.group(1))
        year = int(m_year.group(2))
        if month:
            return f"{year:04d}-{month:02d}"

    m_year2 = re.search(
        r"(\d{4})\s+(january|february|march|april|may|june|july|august|"
        r"september|october|november|december)",
        text, re.IGNORECASE
    )
    if m_year2:
        year = int(m_year2.group(1))
        month = _month_num(m_year2.group(2))
        if month:
            return f"{year:04d}-{month:02d}"

    # Just month name (no year) -- use current year
    m_month = re.search(
        r"\b(january|february|march|april|may|june|july|august|"
        r"september|october|november|december)\b",
        text, re.IGNORECASE
    )
    if m_month:
        month = _month_num(m_month.group(1))
        year = datetime.datetime.utcnow().year
        if month:
            return f"{year:04d}-{month:02d}"

    return None


def _parse_bounds(question):
    """Extract (lo, hi) from phrasing variants.

    Recognised patterns:
      "by X%"           -> lo=X-0.05, hi=X+0.05  (bucket centred on rounded value)
      "increase by X%"  -> same as "by X%"
      "more than X%"    -> lo=X, hi=+inf
      "at least X%"     -> lo=X, hi=+inf
      "less than X%"    -> lo=-inf, hi=X
      "below X%"        -> lo=-inf, hi=X
      "between A% and B%" -> lo=A, hi=B
      "from A% to B%"   -> lo=A, hi=B

    The "by X%" rounding bucket: CPI prints to 1 decimal, so a stated X%
    represents the bucket [X-0.05, X+0.05).  E.g. "0.3%" -> [0.25, 0.35).

    Returns (lo, hi) or (None, None) if unrecognised.
    """
    q = question.lower()

    # "between A% and B%" or "from A% to B%"
    m = re.search(
        r"between\s+(-?\d+\.?\d*)\s*%\s+and\s+(-?\d+\.?\d*)\s*%",
        q
    )
    if m:
        return float(m.group(1)), float(m.group(2))

    m = re.search(
        r"from\s+(-?\d+\.?\d*)\s*%\s+to\s+(-?\d+\.?\d*)\s*%",
        q
    )
    if m:
        return float(m.group(1)), float(m.group(2))

    # "more than X%" / "greater than X%" / "above X%" / "at least X%" / "exceeds X%"
    m = re.search(
        r"(?:more than|greater than|above|at least|exceeds?)\s+(-?\d+\.?\d*)\s*%",
        q
    )
    if m:
        return float(m.group(1)), float("inf")

    # "less than X%" / "below X%" / "under X%" / "at most X%"
    m = re.search(
        r"(?:less than|below|under|at most)\s+(-?\d+\.?\d*)\s*%",
        q
    )
    if m:
        return float("-inf"), float(m.group(1))

    # "by X%" or "increase by X%" or "rise by X%" or "change of X%" etc.
    # This is the bucket-centred form.
    m = re.search(
        r"(?:by|of|to|at)\s+(-?\d+\.?\d*)\s*%",
        q
    )
    if m:
        x = float(m.group(1))
        return round(x - 0.05, 10), round(x + 0.05, 10)

    return None, None


def parse_market(question, slug=""):
    """Parse a Polymarket question into a structured US CPI MoM claim.

    Returns:
        {"indicator": "us_cpi_mom", "period": "YYYY-MM", "lo": float, "hi": float}
    or None if not a parseable US-CPI-MoM market.

    Conservative: abstains on any ambiguity.
    """
    if not question:
        return None

    q = question.lower()

    # Must reference CPI / inflation / consumer price
    cpi_terms = ["cpi", "consumer price", "inflation", "cpi-u", "cpi-all"]
    if not any(t in q for t in cpi_terms):
        return None

    # Must be MoM context
    mom_terms = [
        "month", "monthly", "mom", "m/m", "month-over-month",
        "month over month", "increase by", "rise by", "change of",
        "by 0.", "by 0 ", "by 1.", "by -",
    ]
    # Also accept "increase by X%" phrasing even without explicit "month" keyword
    has_mom_context = any(t in q for t in mom_terms)
    # "Will monthly inflation increase by X%?" has "monthly" -- covered.
    # Also accept "0.X%" phrasing as implied MoM (CPI prints are small numbers)
    if not has_mom_context:
        if re.search(r"\b0\.\d+\s*%", q):
            has_mom_context = True

    if not has_mom_context:
        return None

    # Exclude non-US indicators (UK, China, GDP, YoY annual, etc.)
    if _is_non_us_cpi(question):
        return None

    # Extract period
    period = _parse_period(question, slug)
    if period is None:
        return None

    # Extract bucket bounds
    lo, hi = _parse_bounds(question)
    if lo is None and hi is None:
        return None

    return {
        "indicator": "us_cpi_mom",
        "period": period,
        "lo": lo,
        "hi": hi,
    }
