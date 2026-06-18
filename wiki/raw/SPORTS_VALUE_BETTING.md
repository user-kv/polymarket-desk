# SPORTS VALUE BETTING — Deep Research (RAW)

Captured 2026-06-12. Multi-source verified.

## THE PREMISE (why it's near-unfalsifiable)
- **Pinnacle's closing line ≈ true probability.** Evidence: across **397,935 football games,
  r² = 0.997** between Pinnacle closing lines and actual outcomes. Optimal prediction puts
  **95–100% of weight on Pinnacle** vs all other books.
- Why Pinnacle is sharpest: **"winner's welcome" policy** — it doesn't ban winning bettors;
  it INVITES sharp money and uses it to price lines. Highest liquidity = most information.
- Polymarket sports prices are set by SLOW RETAIL money. Gap between de-vigged sharp line and
  Polymarket price = your edge. "Polymarket reacts in minutes/hours; sportsbooks in seconds."
- ACADEMIC: if you consistently beat Pinnacle's closing price, you're almost certainly
  profitable long-term (Law of Large Numbers).

## DE-VIG (turning sharp odds into true probability)
The "vig" is the bookmaker margin. Strip it so probabilities sum to 100%.
- **Multiplicative** (most common): each side's implied prob ÷ sum of all implied probs. Good
  for 2-way balanced markets. (e.g. implied 0.55 & 0.50 sum 1.05 → 0.55/1.05=52.4%, 0.50/1.05=47.6%.)
- **Power**: uses exponents; accounts for favorite/longshot asymmetry; between multiplicative & Shin.
- **Shin** (most theoretically sound): assumes some vig comes from insider info; gives more margin
  to longshots; iterative; best for heavy favorites / player props / multi-way markets.
- RULE: multiplicative is fine for 2-way; use Shin/power for multi-way or heavy-favorite markets.
- Free devig calculators exist (oddsjam, gamblingcalc, edgeslip).

## CLOSING LINE VALUE (CLV) — the proof-of-edge metric
- Closing line = final odds before the event = most accurate "true probability" (bakes in all
  info: injuries, weather, sharp money).
- **Beating the closing line consistently = mathematically profitable long-term.** It's THE
  metric pros use to know if they have an edge BEFORE results catch up.
- How to beat it: (1) **line shopping** (best price across books), (2) **bet EARLY** (lines are
  soft before sharp money sharpens them), (3) make genuinely +EV bets.
- Track: log your entry price + the closing line for 100+ bets; compute % of bets with positive
  CLV and average CLV.
- BENCHMARKS: positive CLV (even +1–2%) = beating market; **+5% = excellent / strong edge**;
  **60–65% of bets beating CLV over 200+** = consistent edge.

## EXECUTION ON POLYMARKET
- Sports covered: NFL, NBA, MLB, NHL, soccer, UFC, boxing, tennis, F1, Olympics, World Cup.
  Markets: game winners, season outcomes, MVP, championships, some props.
- Workflow: (1) get sharp odds (Pinnacle/Betfair/PS3838), (2) de-vig → true prob, (3) compare
  to Polymarket price, (4) if Polymarket price < true prob by ≥ threshold (after costs), buy &
  **HOLD TO RESOLUTION** (don't try to flip — exit liquidity is poor).
- Threshold: **≥5% edge** commonly cited; need ≥2.2–3.0% just to cover the 2% winner fee + gas +
  slippage, so demand more.
- Tools: OddsJam (edge feed + devig + CLV + prediction-market trader tracker), PredictEngine
  (arb scanner), Pinnacle Odds Dropper, odds APIs (oddspapi). Trackers: polysight.app,
  polytraders.io. Repos: github.com/Alirun/polymarket-trader, jon-becker/prediction-market-analysis.

## SIZING (Kelly)
- Formula: **f = (b·p − q) / b** where b = decimal odds − 1, p = your true prob, q = 1−p.
  f = fraction of bankroll to bet. (e.g. f=5% of $1,000 → $50.)
- Use **Quarter Kelly (0.25×)** — full Kelly assumes you KNOW the true prob (you don't); fractional
  Kelly cuts variance and protects against estimate error. Many use 1/4 or 1/8.
- Bankroll = money you can fully afford to lose.

## ⚠️ FLAWS / RISKS (honest)
- The FAST/biggest edges (15–60s) are bot-contested; don't race them. Value-bet slower/less-liquid
  markets and HOLD.
- **Liquidity:** Polymarket has fewer markets than books; low-liquidity markets are easy to BUY
  but hard to SELL → hold to resolution, size for the available depth.
- **Wash trading** inflates Polymarket volume (Columbia study) → don't trust volume blindly.
- Value betting = highest skill bar (only ~3.14% of accounts "skilled"); rising efficiency = fewer
  easy edges over time. Costs (2% winner fee + spread) must be cleared.
- AU access issue applies (Polymarket blocked in AU).

## SOURCES
- datagolf "how sharp are bookmakers", completesports "how Pinnacle sets sharpest lines",
  Trademate "closing line", Pinnacle Odds Dropper devig guide, OddsJam CLV education,
  predictengine "trade sports on Polymarket", QuantPedia, arxiv 1910.08858 & 2303.16648.
- Video triangulation (youtube_metadata_3_strategies.md): "How To Trade Sports for Profit on
  Polymarket", "Polymarket vs Vegas", multiple CLV tutorials (incl. pro Steve Fezzik),
  "I Built an AI That Finds Mispriced Sports Bets on Polymarket (69.8% Win Rate)".
