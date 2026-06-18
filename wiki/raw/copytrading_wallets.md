# Named Wallets / Top Traders (RAW)

Captured: 2026-06-12. Stats are AS-CLAIMED by sources — verify on-chain / leaderboard before trusting.

---

## WEATHER LEADERBOARD (2026) — source: polymarketweather.com leaderboard, polyburg
| Rank | Wallet | Profit (weather) | Notes |
|---|---|---|---|
| 1 | **gopfan2** | +$351,942 | see detail below |
| 2 | **aenews2** | +$286,705 | |
| 3 | **ColdMath** | +$135,489 | algorithmic, consistent, high-activity |
| - | gopfan | (separate from gopfan2?) | |
| - | bama124 | | |
| - | Hans323 | | latency-arb on model release windows |
| - | Poligarch | | |
| - | Handsanitizer23 | | |
| - | ShyGuy1 | | |

### gopfan2 (FLAGSHIP weather trader)
- Address: **0xf2f6af4f27ec2dcf4072095ab804016e14cd5817**
- Profile: https://polymarket.com/@gopfan2  |  analytics: https://polymarketanalytics.com/traders/0xf2f6af4f27ec2dcf4072095ab804016e14cd5817
- Joined Aug 2024. **2,001 predictions**, 10,000+ individual positions.
- $519.8K positions value, $920.0K biggest win, 193.1K profile views.
- STRATEGY: simple systematic rules applied consistently at scale = "consistent
  identification of mispriced tails at scale." NOT discretionary.
- Lifetime ~$2M claimed across all markets (mostly weather).

### Hans323
- 23yo German law student. Latency-arb around model release windows.
- CONFLICTING profit figures across sources: $1.11M (one London bet) vs ~$81k net weather.
  FLAG to reconcile.

### ColdMath
- Algorithmic weather trader, ~$120k–135k cumulative net. Famous strategy (dedicated article
  exists: polymarketweather.com/blog/coldmath-polymarket — FETCH next).

---

## LEADERBOARD DATA SOURCES (for live vetting)
- Official: https://polymarket.com/leaderboard/weather/all/profit
- Official API: docs.polymarket.com/api-reference/core/get-trader-leaderboard-rankings
- 3rd-party analytics: polymarketanalytics.com/traders , predicts.guru/leaderboard ,
  polyburg.com/polymarket-top-traders , polycopy.app/best-polymarket-traders

---

## OVERALL LEADERBOARD — Polycopy Top 10 by 30-day verified P&L (June 2026)
SOURCE: polycopy.app/best-polymarket-traders
| Rank | Trader | 30d P&L | Volume | Notes |
|---|---|---|---|---|
| 1 | **Inaccuratestake** | +$3.9M | $19.2M | highest monthly profit |
| 2 | **Latina** | +$1.7M | $10.7M | |
| 3 | **afghj2421** | +$1.5M | $8.0M | |
| 4 | **downtownfee** | +$1.1M | $4.0M | |
| 5 | **ferrariChampions2026** | +$947K | $50.6M | LARGEST volume → likely market-maker/bot, low ROI% |
| 6 | 0x6db5...e279 | +$897K | $4.0M | |
| 7 | **Mentallyillgambld** | +$887K | $2.4M | high ROI vs volume |
| 8 | 0xcF60...6847 | +$683K | $10.7M | |
| 9 | **BreakTheBank** | +$545K | $2.3M | high ROI vs volume |
| 10 | **Sassy-Bucket** | +$543K | $9.2M | |

NOTE: high-volume/low-ROI names (ferrariChampions2026) = probably market-makers — NOT
copyable (their edge is liquidity provision, not directional calls). Prefer high-ROI-per-
volume names (Mentallyillgambld, BreakTheBank) for copy candidates — but verify niche + that
they're not just lucky high-rollers. ~23% of 5+ trade wallets are lifetime-positive.

---

## BOT-DOMINANCE REALITY (critical for copy selection)
SOURCE: coinalertnews, polycopy/best-polymarket-bots, quicknode bot guide
- **14 of the top 20 traders are BOTS.** 73% of arbitrage profit captured by sub-100ms bots.
- Bots clear ~$206k at >85% win-rate; humans ~$100k (worse stake sizing/risk).
- Bot categories: (1) **arbitrage** (Binance/Coinbase latency), (2) **market-makers** (spread,
  NOT directional — DO NOT COPY, no replicable signal), (3) **copy bots** (PolyCop etc),
  (4) **news-driven** (NLP on news/social).
- IMPLICATION for copy trading:
  - Many leaderboard kings = arb/MM bots whose edge is **speed/liquidity you can't replicate**.
  - Copying them = you fill at worse prices (latency), edge evaporates, or capital gets
    "trapped" in niche markets with no exit volume.
  - **Only copy DISCRETIONARY/slow research traders** in non-HFT markets (politics, sports,
    long-horizon), where a 1.5s mirror lag doesn't kill the trade.
- Sharky6999 (99.3% WR) + ferrariChampions2026 (huge volume) almost certainly bots → skip.

---

## ⭐ DISCRETIONARY (COPYABLE) TRADERS — all-time, by niche
SOURCE: polycopy.app, laikalabs, gemQueenx Medium. These are HUMAN research traders — the
ones actually worth copying (slow enough that 1.5s mirror lag doesn't kill the trade).
- **Theo4** — ~+$22.1M lifetime / $43.0M volume. Top all-time. (the famous "Théo" French whale)
- **beachboy4** — SPORTS specialist. $4,357,027 on $12.96M vol, **33.6% profit margin**.
  Concentrated: six-figure sums on individual outcomes. Deep league knowledge.
- **HorizonSplendidView** — DIVERSIFIED. $4,016,108 on $12.39M vol, **32.4% margin**.
  Spreads across politics/sports/crypto/econ ~equally. Genuine multi-domain analysis.

## HOW TO TELL DISCRETIONARY vs BOT (copy-selection rule)
- **~100 predictions/month = real research, copyable** (you can keep up manually).
- Crypto BTC/ETH 15-min wallets = bots capturing spread → NOT copyable.
- High profit MARGIN % on big volume + niche focus = genuine edge.
- Tool: **PolySmartWallet** separates traders by category (Politics/Sports/Crypto/Finance/
  Culture) + shows PNL, win rate, score, open positions, live portfolio, PNL chart. BEST for
  finding a real performer in the niche you care about.

## OPEN: pull full Polycopy Top-50; aenews2 + ColdMath + Theo4 addresses; per-niche win rates.
