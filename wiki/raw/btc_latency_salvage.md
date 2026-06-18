# BTC Latency Arb — Salvage Notes (DEPRIORITIZED)

Captured: 2026-06-12. Kept so nothing is lost; not the focus.

## The idea (Kavee's)
Binance/Coinbase move first; Polymarket BTC Up/Down markets lag → trade the gap.

## Reality 2026
- Lag is real: **30–90s on big moves** (MMs not colocated at Binance).
- WAS a goldmine: **~$40M extracted Apr2024–Apr2025**; top 3 arb wallets ~$4.2M/yr.
- **14 of top 20 wallets are bots**; **73% of arb profit = sub-100ms bots**.
- Polymarket KILLED it for non-bots: **dynamic taker fee on 15-min crypto, highest near 50%
  odds (~3.15% on a 50¢ contract) — exceeds the arb margin.** Fee calibrated to eat the edge.
- 5-min BTC market: one source = removed/dead videos; short windows ≈ coin flip after fees.

## If ever pursued (bot-only)
- Need: low-latency VPS near exchanges, WebSocket-first (not polling), maker-rebate optimization.
- Reference repo: github.com/learningworship/polymarket-latency-bot (Python, sim mode) — STUDY only.
- The suislanchez weather bot also has a BTC sub-strategy: RSI+momentum(1/5/15m)+VWAP+SMA,
  needs 2+/4 aligned, min edge 2%, scan 60s, cap $75/trade. Indicator-based, not pure latency.

## VERDICT
Not viable manually. Fees + colocated bots win. Park it; focus weather + copy.
