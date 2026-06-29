from institute.classify.tradeability import check, crude_toxicity


def test_healthy_market_passes():
    ok, reasons = check({"resolvable": True, "exit_depth": 100, "last_trade_age_s": 60,
                         "two_sided": True}, intended_position=1.0)
    assert ok and reasons == []


def test_thin_depth_rejected():
    ok, reasons = check({"exit_depth": 1, "last_trade_age_s": 60, "two_sided": True},
                        k=3, intended_position=1.0)
    assert not ok and "thin-depth" in reasons


def test_stale_price_rejected():
    ok, reasons = check({"exit_depth": 100, "last_trade_age_s": 999999, "two_sided": True})
    assert not ok and "stale-price" in reasons
    ok2, reasons2 = check({"exit_depth": 100, "last_trade_age_s": 1, "two_sided": False})
    assert not ok2 and "stale-price" in reasons2


def test_toxic_flagged():
    _, flag = crude_toxicity({"new_wallet_one_sided": True})
    assert flag
    ok, reasons = check({"exit_depth": 100, "last_trade_age_s": 1, "two_sided": True,
                         "meta": {"new_wallet_one_sided": True}})
    assert not ok and "toxic" in reasons
