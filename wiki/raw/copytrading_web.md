# Copy Trading — Web Research (RAW)

Captured: 2026-06-12. Unvetted.

---

## How copy trading works (2026 mechanics)
SOURCE: polycopytrade.space guide, polyzig, 0xmega Medium
- Polymarket has **NO official built-in copy feature** in the main app. All copy trading =
  **3rd-party non-custodial** platforms that read on-chain trades from a tracked wallet and
  submit mirrored orders signed by YOUR wallet (funds never leave your control).
- 4-step loop: (1) pick wallet(s) from leaderboard/on-chain analytics → (2) platform watches
  Polygon in real time for trades signed by those wallets → (3) on detection, computes a
  proportional mirrored order based on your allocation/risk settings → (4) your wallet signs
  + submits on Polygon.

## Vetting filters (what to look for)
- Win rate **>55–60%** across **200+ trades** (consistency > a few huge lucky bets).
- Positive profit over **7–30 days**, multiple followers.
- "A 70% win rate across 200+ trades beats massive profit from a handful of huge bets."
- Follow **3–5 traders across different categories** for diversification.
- Act on **consensus** (multiple top traders independently same side).

## Risk management rules
- Start with **small allocations**, scale up after verifying performance.
- **Never >2–5% of bankroll on a single trade.**
- Don't copy bots in fast markets — you fill at worse price, slippage kills edge.

## Backtest evidence (Polycopy, 687K+ resolved trades)
- **Copy Score 70+ trades win 67.7% of the time, +5.76% avg P&L.** Lower scores ≈ random.
- Only ~**23%** of tracked wallets with 5+ resolved trades have positive lifetime returns.
  (Other source: only ~12.7% of all users profitable; ~80% of copy targets are traps;
  ~15% of wallets show wash-trading.)

## Tools / platforms (2026)
- **Poly Syncer** (engine behind Stand's official "COPYCAT" w/ Polymarket) — FULL DETAIL:
  - Scores wallets by: realized PnL, win-rate, **Sharpe**, drawdown, **avg hold time**,
    **market diversity**. Refresh every 60s. **Outlier/luck filter: drops z-score > 2.5.**
  - Tracks **12,438+ wallets**, 34,921 copiers, $48.2M mirrored (as-claimed).
  - **FREE = view-only** (leaderboard + methodology, NO execution).
  - **Pro = $299/mo**: copy up to 250 wallets, unlimited daily trades, dedicated RPC
    ~1.5–1.8s latency (p99 <600ms), all 25 categories, core risk controls.
  - **Elite = $499/mo**: unlimited copies, co-located RPC ~0.6s, AI alpha discovery,
    mempool sniping, hedge mode, quant support.
  - Latency chain: leader detect ~120ms → contract event ~80ms → listener ~150ms →
    risk/sizing ~250ms → mempool submit ~250ms → confirm ~1.0s.
  - Risk controls: per-wallet allocation weighting, max position size, daily/weekly loss
    caps, time-of-day windows, category filters, slippage protection, trailing stops.
  - Sizing: **Kelly + fixed-fraction**, variance cap 0.25. Min funding **$25 USDC**.
  - NOTE: free tier is view-only here (differs from earlier source claiming free 1-wallet
    copying — FLAG/verify; tiers may have changed).
- **PolyCopyTrade** ("Smart Score" algo). **HolyPoly** (hourly leaderboard, trade-count filters).
- **PolySmartWallet** — has BACKTEST: shows how copying a wallet would've performed incl slippage.
- Others named: polycop, polygun, kreopolybot, polyapex, Telegram copy bots, Polycule Bot.

## OPEN THREADS
- Pull full Poly Syncer ranking methodology + Pro pricing.
- Confirm which top-10 (below) are bots vs discretionary (avoid copying bots in fast mkts).

## SOURCES
- https://www.polycopytrade.space/blog/what-is-polymarket-copy-trading/
- https://polyzig.com/guides/how-to-copy-trade-polymarket
- https://medium.com/@0xmega/how-to-copytrade-on-polymarket-full-beginners-guide-d4a398b896e9
- https://www.polyfollow.com/best-polymarket-traders-to-follow
- https://polycopy.app/how-to-copy-trade-polymarket
- https://www.polysyncer.com/  |  https://www.holypoly.io/blog/best-polymarket-copy-trading-tools-2026
