# PRACTICAL BLOCKERS — Access, Fees, Capital (READ FIRST)

Captured: 2026-06-12. These gate EVERYTHING below the strategy layer.

---

## 🚨 #1 BLOCKER: POLYMARKET IS BLOCKED IN AUSTRALIA (Kavee is .au)
SOURCE: startpolymarket.com/countries/australia, polymarket-australia.com, tradetheoutcome
- **Blocked since Aug 13, 2025**: ACMA ordered ALL Australian ISPs to block Polymarket,
  classifying it a **prohibited interactive gambling service**. Government ISP-level block,
  not just Polymarket's own geoblock — one of the stricter blocks globally.
- **VPN does NOT fix the legal position.** Your physical location in AU at transaction time
  sets your regulatory obligations. VPN may bypass the IP block technically but **breaches
  Polymarket ToS** (restricted-jurisdiction use).
- **NO Australian regulator can compel Polymarket to release your funds.** ACMA is adversarial,
  not cooperative — if funds get stuck/frozen, there's no recourse for AU users.
- IMPLICATION: Before ANY of this, Kavee must decide how he's accessing — and accept the
  legal/funds-recovery risk. Options to research with him: (a) is he actually AU-resident /
  AU-tax? (b) Kalshi (US-regulated, the weather-bot repos ALSO trade Kalshi KXHIGH series) —
  check Kalshi's AU stance; (c) other prediction venues. **This is a go/no-go gate.**
- NOTE: the open-source weather bots (suislanchez, alteregoeth) support **Kalshi** too —
  may be the cleaner venue depending on jurisdiction. WORTH a dedicated Kalshi-from-AU check.

## 🚨 #1b: KALSHI ALSO BLOCKS AUSTRALIA
SOURCE: pokerscout (Kalshi global launch), datawallet
- Kalshi went "global" (143 countries) BUT **explicitly excludes Australia, UK, Canada.**
- Kalshi is CFTC-regulated; restricted-region users **cannot open accounts, deposit, or trade.**
- So the two biggest weather/temperature venues BOTH exclude AU. → The venue problem is real
  and not solved by just switching to Kalshi.
- REMAINING OPTIONS to research with Kavee (all need due diligence): other prediction
  exchanges that accept AU; trading via a non-AU entity/residency he legitimately has;
  or treating this as research-only until access is sorted. **Do NOT hand-wave the legal gate.**

## #2: FEES (matters for the thin weather edge)
SOURCE: docs.polymarket.com/trading/fees, marketmath.io, predictionhunt
- **Weather markets: 1.25% TAKER fee** (as of Mar 2026).
- Formula: `fee = C × feeRate × p × (1-p)` → **peaks at 50¢**, ~0 near $0.01/$0.99.
  (So tail-bucket buys at 5–15¢ are CHEAP on fees; central 50¢ buys cost most.)
- **MAKERS pay ZERO** (limit orders that add liquidity). Takers can get 20–25% rebate via
  Maker Rebates Program. → Posting limit orders instead of market orders saves the fee.
- Crypto markets: dynamic taker fee (the BTC arb killer). Geopolitics/world events: FEE-FREE.

## #3: SPREADS (the hidden cost, worst exactly where the edge is)
- Spread = hidden cost every trade. Liquid markets 1–2¢; **niche markets 5–10¢ (=5–10%
  round-trip)**. Avg spread tightened 4.5% (2023) → 1.2% (late 2025).
- ⚠️ TENSION: the edge lives in **secondary cities (low liquidity)** — but those have the
  **widest spreads**. So the 8–10% EV threshold must clear **1.25% fee + 5–10% spread**.
  Real net edge needed is higher than the headline 8%. → use LIMIT orders (maker, 0 fee) and
  only trade when EV comfortably beats spread+fee.

## #4: CAPITAL / FUNDING
- USDC on Polygon. Fund via Coinbase direct USDC, or bridge from ETH/Base/Arbitrum/Solana.
- KYC: photo ID + selfie for full access.
- Bot start: ~$10 USDC.e + ~2 POL (~$1) gas (per Hermes guide). Real edge needs portfolio
  scale (10–30+ positions) → realistically a few hundred $ min to diversify properly.

## BOTTOM LINE
Strategy is solid, but **access/jurisdiction is the real first question for an AU user.**
Resolve the venue (Polymarket-via-? vs Kalshi vs other) BEFORE building anything.
