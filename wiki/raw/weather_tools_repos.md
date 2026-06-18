# Weather — Tools, Repos, APIs (RAW)

Captured: 2026-06-12.

---

## ⭐ REPRODUCIBLE BOT BLUEPRINT — github.com/suislanchez/polymarket-kalshi-weather-bot
Most actionable find. Open-source, paper-trading. Trades weather on Kalshi + Polymarket AND
BTC 5-min on Polymarket. Architecture is directly reusable.

### Weather signal (the core method)
- Pull **31-member GFS ensemble** from **Open-Meteo** (free).
- Count how many of the 31 members exceed the market's temperature threshold.
- That fraction = model probability. (e.g. 25/31 above threshold → 80.6% implied.)
- Trade when **model prob vs market price edge ≥ 8%**.
- Calibration: track predictions vs outcomes with **Brier score**, refine over time.

### Position sizing (fractional Kelly)
- `kelly = (win_prob * odds - lose_prob) / odds`
- Apply **15% Kelly fraction × bankroll**, capped at **$100/weather trade** ($75/BTC trade).
- Additional cap: **5% of bankroll max per position**.
- Default bankroll in repo: $10k.

### Markets / cities
- Kalshi **KXHIGH** series: NYC, Chicago, Miami, Los Angeles, Denver.
- Polymarket weather + BTC via **Gamma API**.

### BTC sub-strategy (salvage interest)
- Indicators: RSI, momentum (1m/5m/15m), VWAP, SMA crossover, from Coinbase/Kraken/Binance candles.
- Needs **2+ of 4 indicators aligned**. Min edge 2%. Scan every 60s. (Weather scans every 300s.)

### Stack / run
- Backend: FastAPI + SQLAlchemy + APScheduler. `pip install -r requirements.txt` →
  `uvicorn backend.api.main:app --reload --port 8000`.
- Frontend: React+TS, `npm install && npm run dev` → localhost:5173.
- Results: "highest profits $1.8k" in PAPER mode (not live).

---

## ⭐⭐ REPO #0 (BEST) — github.com/natestokens/polymarket-weather-bot
Built with Claude Code. Most detailed + HONEST verified results. Full notes in youtube_findings.md.
- **173-member ensemble**: ECMWF IFS + ECMWF AIFS + NCEP GEFS + ICON via Open-Meteo.
- **City bias correction** vs ASOS airport history (NYC +1.4°F, Miami −2.2°F, Chicago +1.4°F).
- Edge = model_prob − market_price. Thresholds: **5pp for NO, 15pp for YES** (asymmetric).
- "Stay away from the middle": 3°F buffer around ensemble mean.
- **Pure Python, zero dependencies.** bot.py / verify.py / signals.csv.
- Verified: **+27.6% ROI, 60.9% win, +$77 on $279** (May 27 2026) — credible, not hype.

## ⭐ REPO #2 — github.com/alteregoeth-ai/weatherbot (the one Hermes forks)
"Kelly Criterion + EV filtering + simulation mode." Simpler/more focused than repo #1.
- **Strategy:** compare real-time forecast to market price; trade when price < entry threshold
  AND expected value positive. "Skips trades where the math doesn't work."
- **Data:** ECMWF & HRRR via **Open-Meteo** (free), **METAR** (real-time airport obs),
  **Visual Crossing** (historical temps for resolution), **Polymarket Gamma API** (prices).
- **Coverage:** 20 cities / 4 continents, major airports (KLGA for NYC, KDAL for Dallas).
- **config.json defaults:** min EV 0.05 | max price 0.45 | max bet $20 | min volume 2,000 |
  Kelly fraction 0.25 | max slippage $0.03 | scan interval 3,600s (hourly).
- **Run:** `python weatherbot.py` (scan) | `python weatherbot.py status` | `... report`.
- This is the cleanest starting point for a real bot; Hermes just wraps it in an agent.

## NEW named performers (from build articles, AS-CLAIMED, verify)
- **Sharky6999** — 99.3% win-rate, $819K PnL (suspiciously high → likely arb/MM; FLAG).
- **ColdMath** — $300 → $219K in 3 months (broader figure than $120K weather-only; reconcile).

## FREE DATA APIs (log for build)
- **Open-Meteo** — GFS/ECMWF/etc incl 31-member GFS ensemble. Free, no key. ← primary
- **api.weather.gov (NWS)** — official US forecasts + observations; matches many US resolutions.
- **Polymarket Gamma API** — market data/prices. docs.polymarket.com
- Model run schedule (UTC): GFS 00/06/12/18, ECMWF 00/12.

## Other tools / bots seen
- **StormBot.Ai** (stormbot? commercial weather bot, 24/7) — video npy1rzBOl6M.
- **WeatherBot.fi** — commercial AI weather trading bot.
- **Polyburg** — "whale intelligence" weather dashboard.
- Multiple YouTube "build weather bot with Claude Code" tutorials (hej22I5Sit4).
- Dev.Genius article: built a free weather bot, claims bots making $24k (FETCH via redirect — pending).

## KEY INSIGHT
The whole edge = casual bettors price markets on gut feeling; systematic ensemble-vs-price
comparison exploits the mispricing. As long as casuals keep entering, mispricings persist.
Bots compressed major-city windows to 5–15 min; secondary cities still have hours.

## SOURCES
- https://github.com/suislanchez/polymarket-kalshi-weather-bot
- https://github.com/learningworship/polymarket-latency-bot
- https://blog.devgenius.io/found-the-weather-trading-bots-quietly-making-24-000-on-polymarket-...
- https://weatherbot.fi/  |  https://stormbot (via video)  |  https://polyburg.com/polymarket-weather
- Open-Meteo: https://open-meteo.com  |  NWS: https://api.weather.gov
