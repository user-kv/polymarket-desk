"""Resolved-market aggregation across archetypes."""
from institute.resolve import weather_adapter, crypto_adapter


def load_all_rows():
    """All settled ResolvedMarket rows from every wired adapter (weather + crypto)."""
    return weather_adapter.load_rows() + crypto_adapter.load_rows()
