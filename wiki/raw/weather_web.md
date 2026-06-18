# Weather Markets — Web Research (RAW)

Captured: 2026-06-12. Unvetted.

---

## How the edge works (core thesis)
SOURCE: laikalabs.ai weather guide, polymarketweather.com
- Edge = **information asymmetry** between pro forecast models and current market price.
  Not meteorology skill — it's reacting to model updates faster than the market reprices.
- Pro models update on a **fixed 6-hour clock**; Polymarket prices lag the new run.
- The lag window: **5–15 min on active markets (NYC/London)**, but **HOURS on secondary
  cities** (Buenos Aires, Cape Town, Atlanta) with wider spreads + fewer bots.

## Model update schedule (UTC)
- **GFS** (NOAA): 00:00, 06:00, 12:00, 18:00
- **ECMWF**: 00:00, 12:00
- Free data: **Open-Meteo** + **api.weather.gov** (NWS) — can fetch GFS/ECMWF/UKMO/NWS in parallel.

## Pro entry rule (buy YES on temp bucket) — ALL four must hold:
- (a) ensemble-implied probability **≥ 8% above** current YES ask
- (b) lead time **≤ 48 hours**
- (c) GFS and ECMWF ensemble means **agree within 1.5°C** on city's daily high
- (d) market has **≥ $10,000** total volume

## Worked example
- 12:00 UTC GFS run: cold air into NYC faster than expected, high 62°F → 54°F for tomorrow.
- "55–59°F" bucket was $0.18; correct post-update price ~$0.55+. Buy before market catches up.

## Structural edges
1. **Airport-vs-city-center**: markets resolve at a specific AIRPORT station; retail uses
   city-center readings. Gap is predictable. E.g. **LaGuardia (KLGA) runs 3–5°F cooler than
   Midtown Manhattan** in summer sea-breeze events.
   - BIGGEST RISK: trading off the wrong weather station vs the actual resolution source.
2. **Temperature laddering**: buy several adjacent buckets cheap (0.2¢–15¢); one/two hits
   cover the misses.
3. **Portfolio**: run **10–30+ city/date combos** small; profit only shows statistically
   over hundreds of independent trades.

## Best cities (2026)
- **Secondary > major.** Buenos Aires, Cape Town, Atlanta = persistent edge windows (hours).
- NYC / London / Hong Kong / Miami = high volume, bot-saturated, edge gone in 5–15 min.
- 2025 was easier (BA had very wide spreads); 2026 more competitive — discipline in
  secondary markets is where profit is.

## ⭐ NO-CODE MANUAL STARTER PLAYBOOK (do this first, no bot needed)
SOURCE: Ezekiel Njuguna, medium.com/mountain-movers "...I will teach you how"
Free visual tools instead of APIs:
- **Tropical Tidbits** — raw GFS/ECMWF model output (visual).
- **Windy** — "Compare models" feature (GFS vs ECMWF vs ICON side by side).
- **NOAA Climate Data Online** — historical context.
- Resolution refs: Weather Underground (London), NOAA (NYC).

THE RULE (manual):
1. Pick **1–2 cities** (he uses NYC + London — note: high liquidity but bot-heavy; for edge
   prefer the secondary cities from ColdMath: Buenos Aires/Cape Town/Dallas/Atlanta).
2. Daily, check 1–3 day temperature markets.
3. Record GFS + ECMWF + ICON forecasts.
4. **When 3+ models agree on a temp range → true prob ~70–90%.**
5. Compare to Polymarket odds. Act ONLY on obvious mismatch:
   - Buy **YES below $0.15** when models strongly support.
   - Buy **NO above $0.45** when models oppose.
6. Trade forecast SHIFTS right after model runs (GFS 00/06/12/18 UTC; ECMWF 00/12 UTC),
   before the market reprices.
7. **Bet $1–$3/trade, 1–5 trades/day max.** Log every trade.
8. Hold to resolution at first; advanced = exit on repricing.
9. **Document 100+ trades before scaling stakes.** Target 70–80% win rate via selective entry.
This is the cheapest way for Kavee to learn the edge by hand before automating.

## Documented profits (named)
- **gopfan2** — ~$2M lifetime, mostly weather (see wallets file for detail).
- **Hans323** — $1.11M on one low-prob London bet (8% odds, $92,632 position). NOTE conflicting
  figure: one source says ~$81k net on weather, 23yo German law student, latency-arb around
  model release windows. FLAG: reconcile later.
- **1pixel** — $18,500 from $2,300 deposited, trading only NYC + London.
- **ColdMath** — ~$120k–135k cumulative net from weather; consistent high-activity ALGO trader.

## ⭐ EXACT RESOLUTION RULES (critical — trade the right station!)
SOURCE: docs.polymarket.us/faqs/weather-faqs, minutetemp.com, wethr.net
- Settles on the **NWS Daily Climate Report (CLI)** from the local Weather Forecast Office —
  official high/low/avg from 1-minute raw sensor data (no extra rounding layer).
- **Specific AIRPORT station per market**, fixed at market creation, listed in each market's
  Rules section:
  - **NYC → LaGuardia (KLGA)**
  - **Dallas → Love Field (KDAL)** — NOT DFW
  - (verify each city's station on the market page before trading)
- **Settlement: 8:00 AM ET** the day AFTER the contract date.
- If CLI disagrees with the 24h METAR for the location, settlement may be **delayed to 11:00 AM ET** for review.
- Resolution source is FIXED at creation and never changes.
- BIGGEST avoidable loss = analyzing the wrong station (city-center vs airport).

## ColdMath strategy detail (barbell)
SOURCE: polymarketweather.com/blog/coldmath-polymarket
- **Barbell:** many small positions on underpriced TAIL buckets (5–15¢ YES w/ real non-trivial
  prob) + occasional higher-conviction bets on CENTRAL buckets when model consensus is strong.
- Forecast layer: ensemble temps (GFS/ECMWF or commercial aggregator) at the resolution-station coords.
- Algorithmic: scans buckets where model prob > market price by a set threshold, sizes uniformly.
- "Sophistication is in discipline + consistency, not exotic modeling."
- Cities: **Buenos Aires, Cape Town, Dallas, Atlanta** (lower bot saturation, wider spreads).
- ~$120k+ cumulative net (weather leaderboard).

## Risks
- Bots run 24/7 and compressed the major-city gap to 5–15 min.
- Single freak weather event wipes a concentrated position → diversify.
- Wrong-station error = confident trade on irrelevant data.

## SOURCES
- https://laikalabs.ai/prediction-markets/trade-polymarket-weather-markets
- https://polymarketweather.com/blog/polymarket-weather-strategy
- https://polymarketweather.com/blog/coldmath-polymarket
- https://polymarketweather.com/blog/polymarket-weather-leaderboard
- https://polymarket.com/weather  |  https://polymarket.com/weather/low-temperature
