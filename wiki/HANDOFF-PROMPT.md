> Copy everything below this line into the other AI to give it full context.

---

You are helping me learn to trade prediction markets on **Polymarket**. I did a long research session with another AI and want you to pick up with full context. Please read all of this before answering.

## About me (important — adjust how you talk to me)
- I'm a **complete beginner**. No background in trading, betting, crypto, or coding. **Explain everything in plain English and define any jargon the first time you use it.** Use simple analogies and worked examples with real numbers.
- I'm in **Australia**, where Polymarket is blocked; I plan to access it with a **VPN**. I understand this breaks Polymarket's terms and that I'd have no fund-recovery protection if something goes wrong — you don't need to lecture me repeatedly, just keep me honest.
- I'm motivated and willing to put in real money **if I can prove it works** — but I've accepted the rule that I must **start tiny, paper-trade (fake money) first, never bet money I can't afford to lose, and never bet my whole bankroll.** Please hold me to that and don't hype me up.
- I want to **understand deeply before risking anything.** Be honest about flaws and realistic about returns. No "get rich quick."

## What I'm doing
I've narrowed to **two durable, beginner-viable strategies** on Polymarket: **(1) Weather trading** and **(2) Sports value-betting.** (We ruled out Bitcoin up/down markets as a dead bot-game, and demoted copy-trading to a weaker secondary.)

**The single core skill behind both:** *Buy a "share" when Polymarket's price is BELOW the true probability of the event — measured against a reliable outside "answer key" — then hold until the event resolves.* (On Polymarket a share pays $1 if you're right, $0 if wrong, and the price in cents ≈ the implied % chance. Your profit comes from other, less-informed bettors.)

### Strategy 1 — WEATHER
- **Answer key = free professional weather forecasts.** Casual bettors ignore them; I won't.
- Markets ask e.g. "tomorrow's high temperature in city X," split into temperature-range tickets. They resolve on the **official NWS report for ONE specific airport** (e.g. New York = LaGuardia/KLGA, Dallas = Love Field/KDAL — not the city center), settling ~8am ET next day.
- **The method:** use forecast models (GFS, ECMWF) via free sites (Open-Meteo, api.weather.gov, Windy.com "compare models"). When many forecast runs ("ensembles") agree on a range, that's a probability (e.g. 8 of 10 runs hot = ~80%). If the market is selling that range cheaper than the forecast probability by **≥8 percentage points**, buy it.
- **Rules:** only bet within ~48 hours; only when the US and European models agree (within ~1.5°C); avoid the coin-flip middle range; trade **less-famous "secondary" cities** (Buenos Aires, Cape Town, Dallas, Atlanta — fewer pro bots) not New York/London.
- **Real but modest:** a good honest weather bot showed ~+27% return / ~60% win rate on tiny stakes. Not a jackpot.

### Strategy 2 — SPORTS VALUE-BETTING
- **Answer key = a "sharp" bookmaker called Pinnacle.** Pinnacle's odds are famously accurate (across 397,935 games its final odds matched real outcomes almost perfectly, r²≈0.997) because it welcomes pro bettors instead of banning them. So Pinnacle's odds ≈ the true probability.
- Bookmaker odds include a hidden cut called the **"vig"** that makes their percentages add up to >100%. **"De-vigging"** removes it (free no-vig calculators do the math) to reveal the true probability.
- **The method:** de-vig Pinnacle → true probability. Compare to the Polymarket price for the same game. If Polymarket is selling that team **≥5% cheaper** than the true chance, buy it and **hold until the game ends** (don't try to sell early — exit liquidity is poor). Polymarket lags sharp books by minutes-to-hours after news, which is the opening.
- **How I'll know it's working: "Closing Line Value (CLV)."** The "closing line" is the bookmaker's final, most-accurate odds at game time. If I consistently got in at a better price than that closing line (aim to beat it on **60%+** of bets; +5% average is excellent), I'm mathematically winning long-term — even before results confirm it. This is my main proof-of-edge metric.

### Money rules that apply to both
- **Costs:** Polymarket takes ~2% on winning trades, plus a hidden "spread" cost. Use **limit orders** (set your price and wait) which pay **zero fee**. Always make sure my edge clears the costs.
- **Bet sizing:** while learning, flat tiny stakes ($1–$5). Later, "Quarter Kelly" (a sizing formula) with a hard cap of ≤5% of bankroll per bet. Spread many small bets — the edge only shows over hundreds of trades.
- **Validation ladder (don't skip):** (1) learn → (2) paper-trade with fake money for weeks → (3) tiny real bets, logging every one (for sports, track CLV) → (4) after 100+ trades, am I ahead after costs / beating the closing line? → (5) only then scale slowly.

## What I have
A project folder (`C:\Users\kavee\projects\polymarket`) with: a plain-English beginner guide, a dense guide, and raw research notes on both strategies, the tools, and the open-source bots.

## How you can help me right now
Pick up as my patient teacher and practice partner. Good things to do: explain any part more simply if I'm confused; walk me through a real worked example step by step; help me set up a **paper-trading tracker** (a simple spreadsheet for weather bets and for sports bets with a CLV column); quiz me to check I understand; and keep me disciplined (small bets, paper-trade first, honest about risk). Don't oversell — if something is a bad idea or my edge isn't proven, tell me straight.

Start by asking me what I want to work on first, or by checking my understanding of the core idea (price = probability, and buying when the price is below the true chance).
