"""A4 portfolio/book.py: orchestrator smoke tests."""
from institute.portfolio import book


def test_build_book_returns_expected_keys():
    """build_book() must return dict with eligible, gate4, allocation."""
    b = book.build_book(log=False)
    assert "eligible" in b
    assert "gate4" in b
    assert "allocation" in b


def test_live_book_all_reserve():
    """With live data (weather cell gate1_insufficient), allocation is empty,
    reserve equals bankroll. This is the system working correctly."""
    b = book.build_book(bankroll=10000.0, log=False)
    alloc = b["allocation"]
    assert alloc["allocations"] == [], f"expected empty allocations, got {alloc['allocations']}"
    assert alloc["reserve"] == alloc["bankroll"]
    assert alloc["deployed"] == 0.0


def test_render_is_ascii():
    """render() must produce .isascii() output (Windows cp1252 safe)."""
    b = book.build_book(log=False)
    rendered = book.render(b)
    assert rendered.isascii(), "render() produced non-ASCII output"


def test_render_does_not_crash():
    """render() must not raise on live (empty) book."""
    b = book.build_book(log=False)
    rendered = book.render(b)
    assert len(rendered) > 0


def test_render_contains_reserve_message():
    """When no cells graduated, render shows the all-reserve message."""
    b = book.build_book(log=False)
    rendered = book.render(b)
    assert "all reserve" in rendered or "no cells graduated" in rendered
