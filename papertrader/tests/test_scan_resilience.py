"""
tests/test_scan_resilience.py

Verify that cmd_scan returns cleanly (None, no raise) when the Gamma API or
CLOB enrichment call fails with a transient network/JSON error. This ensures
the GCP cron `&&` chain can still proceed to `settle` and `git push` even
when the upstream API is flaky.
"""

import pytest
import papertrader


@pytest.fixture()
def cfg():
    """Load the real config so we don't have to guess every key cmd_scan reads."""
    return papertrader.load_config()


def test_scan_survives_market_fetch_failure(monkeypatch, cfg):
    """Step 1 failure: fetch_weather_markets raises — cmd_scan must return None, not raise."""
    monkeypatch.setattr(
        papertrader.polymarket,
        "fetch_weather_markets",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    result = papertrader.cmd_scan(cfg)
    assert result is None


def test_scan_survives_enrich_failure(monkeypatch, cfg):
    """Step 2 failure: enrich_markets_with_prices raises — cmd_scan must return None, not raise."""
    monkeypatch.setattr(
        papertrader.polymarket,
        "fetch_weather_markets",
        lambda *args, **kwargs: [{"city": "X"}],  # non-empty → passes the guard
    )
    monkeypatch.setattr(
        papertrader.polymarket,
        "enrich_markets_with_prices",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom2")),
    )
    result = papertrader.cmd_scan(cfg)
    assert result is None
