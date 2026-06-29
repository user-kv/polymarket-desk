# The Constitution — Edge, and the Gate That Proves It

*Foundational spec for the autonomous prediction-market forecasting institution. This document defines what "edge" means, how it is measured, and the sequence of gates a strategy must pass before it touches money — paper or real. Everything downstream (architecture, models, hardware) serves this document. If this is wrong, nothing else matters.*

**Status:** v0.1 — ratified parameters from owner (2026-06-28). Principles are stable; numeric parameters are tunable but changes are logged, never silent.

---

## 0. The one-sentence purpose

Find the small set of markets where we add information the price doesn't already contain, prove it on data we have never seen, and deploy capital there — cell by cell, only as each one earns it.

---

## 1. Definitions

- **Market** — a single binary (or bucketed) prediction-market contract with an objective resolution and an executable order book.
- **Archetype** — a class of market sharing a predictability structure and data source (e.g. `weather-daily-temp`, `sports-game-winner`, `crypto-daily-close`, `econ-release`).
- **Strategy / predictor** — a procedure that maps a market's point-in-time context to a probability and a bet decision.
- **Cell** — a `(archetype × strategy)` pair. The cell is the atomic unit of edge. The "predictability map" is the grid of all cells, each coloured by its measured, gated edge. Capital is activated per cell, never globally.
- **Decision time `t₀`** — the instant a bet would be placed. All features must be knowable at `t₀`; all prices used are those executable at `t₀`.
- **Market baseline `q`** — the market-implied probability at `t₀`, taken from the **executable** side (you pay the ask to buy, hit the bid to sell), not the mid.
- **Our forecast `p`** — the strategy's probability at `t₀`.

---

## 2. The Score — information beyond the price

We do **not** score on raw accuracy. (A forecaster can match the market's Brier score and still be highly profitable by losing less when wrong — the documented source of LLM edge. A pure-accuracy metric would discard exactly that edge.)

The score is the **market-relative log score** (incremental skill over the price):

```
S = log_score(p, outcome) − log_score(q, outcome)
  = [ y·ln p + (1−y)·ln(1−p) ] − [ y·ln q + (1−y)·ln(1−q) ]      (y ∈ {0,1})
```

`S > 0` means our forecast added information the price lacked. This is a strictly proper scoring rule expressed relative to the market prior — the mathematically correct formalisation of "beat the price," and it cannot be gamed by hedging or by copying the price (copying the price scores exactly 0).

**Accuracy and calibration are diagnostics, not objectives:** we track Brier, reliability curves, and Expected Calibration Error (ECE) because miscalibrated confidence makes sizing unsafe — but they gate, they don't optimise.

---

## 3. The Objective — risk-adjusted EV after all frictions

`S` says we have *information*. The objective says we can *make money with it*. The objective is **expected value per dollar at risk, net of every friction, sized by calibrated confidence:**

```
EV_net = p·(payout_if_win − 1) − (1−p) − costs
costs  = spread_crossed + fee + expected_slippage + adverse_selection_buffer
```

A bet qualifies only if `EV_net > 0` at **executable** prices with **realistic fills** given observed depth. Backtests scored on mid-price are rejected on principle — they are the "50% backtest → negative live" failure mode. Sizing is fractional-Kelly on `EV_net` and the cell's *calibrated* confidence (§7).

**Secondary fast-feedback diagnostic (not a gate):** for slow signals we may track whether our forecast predicts the *direction the market price subsequently moves* (price convergence) as early, noisy evidence — used to triage what to keep watching, never to promote.

---

## 4. The Universe — tradeability and integrity are preconditions

A market enters the tradeable universe only if **all** hold at `t₀`. An "edge" on a market failing any of these is a fake edge.

1. **Resolvable** — unambiguous, single, reliable resolution source. (We have been burned by resolution quirks before; this is non-negotiable.)
2. **Exitable** — order-book depth ≥ `k ×` intended position on the side we'd exit. At the $1k–$10k scale this is a modest bar, but it is still checked — a fill you can't reverse is a trap.
3. **Not insider-dominated** — flagged-and-excluded when on-chain/price signatures indicate a single informed counterparty we cannot out-inform (the "am I the sucker?" filter).

**Initial universe = fast-resolving archetypes only** (resolution ≤ ~7 days): weather-daily, sports-game, crypto-daily/weekly, econ-release. Rationale: statistical power in weeks, not years. Slow archetypes (politics, long-horizon) are deferred until the loop is proven on fast ones.

**Scale note:** target deployment is $1k–$10k, so the long tail is *in play* — edge density outranks market depth, and thin niche markets the giants ignore are legitimate hunting grounds, subject only to the exitability check above.

---

## 5. Out-of-sample protocol + the trial registry

- **Purged, embargoed walk-forward.** Train/search on past, evaluate on future, with a purge+embargo around each evaluation window so no information leaks across resolution dates. No strategy ever sees an outcome that postdates its decision time.
- **The trial registry.** *Every* hypothesis the research swarm ever tests — including the thousands that fail — is logged with its search context. Overfitting corrections (§6) deflate against the **true** number of trials. Uncounted trials are how multiple-testing corrections lie; we count every fork in the path.

---

## 6. The Gate Stack — what money must pass through

A cell traverses these **in order**. Most ideas die early. Surviving all seven is the only definition of "has edge."

**Gate 1 — Statistical significance, deflated.**
Positive market-relative skill (`mean S > 0`) and positive `EV_net`, significant after multiple-testing correction: **Deflated Sharpe Ratio** and **Probability of Backtest Overfitting** (PBO via combinatorially-symmetric CV), cross-checked against a **permutation null** (shuffle outcomes to get the null distribution of the metric at our true search intensity). Filters; does not promote.

**Gate 2 — Mechanism.**
The cell must state *why* the edge exists — a causal or behavioural reason (favorite-longshot bias, recency over-reaction, liquidity vacuum, model-vs-crowd information gap) — and the reason must be consistent with the error pattern. Significant edge with no plausible mechanism is treated as a probable fluke and held, not promoted. (This is where the LLM judges, rather than computes.)

**Gate 3 — Adversarial red-team.**
An independent agent actively tries to break the cell: hunt lookahead/data leaks, find the regime where it dies, stress the fill assumptions. Must survive.

**Gate 4 — The forward lockbox (the supreme gate).**
Promotion to real capital requires performance on data that **did not exist when the cell was frozen** — i.e. live paper-trading forward. **Bar (moderate): ≥ ~50 resolved live-paper outcomes AND ≥ ~4–6 weeks forward**, with skill and `EV_net` still positive and calibration in band. Backtests nominate; only the genuine future promotes.

**Gate 5 — Portfolio margin.**
Edge is measured as **marginal** contribution to the book's risk-adjusted return after correlation, not standalone. A cell correlated with what we already run (shared macro drivers — markets, like our weather cities, move together) must *improve the book*, or it waits.

**Gate 6 — Capital activation (granular).**
Real capital turns on **per cell**, never via a global switch, and ramps with continued live evidence. Most cells remain paper indefinitely; that is the system working, not failing.

**Gate 7 — Decay / demotion (continuous, symmetric).**
A change-point/decay detector monitors every live cell. When live edge erodes below significance (edges die as competition arrives), the cell is **auto-demoted** to paper or retired. The gate that promotes also fires in reverse.

> The whole pipeline: **backtests propose → statistics filter → mechanism justifies → red-team attacks → forward-paper disposes → portfolio allocates → decay retires.** Risk is not a phase; it is these seven gates. That *is* the low-risk guarantee, built into the physics.

---

## 7. Sizing and risk control

- **Fractional Kelly** on `EV_net`, scaled by the cell's calibration quality (poorly-calibrated cells get cut, not just trusted less).
- **Per-cell drawdown halts — owner-set, with a recommended default.** Each cell carries an explicit `max_drawdown_live` set at activation. **Default if unset: −20% per cell, −15% at the book level.** No cell goes live with an unset limit.
- **Correlation-aware exposure caps** per cell, per archetype, per correlated cluster, and total. Longshot-fade tail-risk is explicitly bounded (one black swan must not erase many small wins — the shape we already saw in the −$100 weather boundary loss).
- **Reserve** kept uncommitted for new opportunities and shocks.

---

## 8. Immutable invariants (the kernel)

These are hash-guarded, enforced by an independent overseer, and may not be edited by the research swarm:

1. **Fake-money-only until a cell clears Gate 4.** No real capital on unproven cells, ever.
2. **The fitness definition (§2, §3) is frozen.** The optimiser is assumed adversarial to the metric; the metric is defined on executable, point-in-time, cost-inclusive, forward-validated terms so the only way to score high is to be genuinely right about the future. No cheaper path exists to exploit.
3. **The trial registry and the lockbox are inviolable.** No strategy may read post-freeze data before Gate 4; no trial may go uncounted.
4. **The gate order is fixed.** A cell cannot reach capital without passing all seven.

---

## 9. What can change vs what cannot

- **Cannot change** (kernel, §8): fake-money-until-Gate-4, the fitness definition, the registry/lockbox, the gate order.
- **Can change** (logged, never silent): numeric thresholds (the `k` depth multiple, the DSR/PBO cutoffs, the Gate-4 sample/time bar, Kelly fraction, drawdown defaults), the archetype roster, the model routing, the data sources.

---

## 10. Ratified parameters (v0.1)

| Parameter | Value | Per-cell? |
|---|---|---|
| Capital scale (ultimate) | $1k–$10k | — |
| Initial universe | fast-resolving only (≤ ~7 days) | — |
| Gate-4 live-paper bar | ≥ ~50 resolved outcomes AND ≥ ~4–6 weeks forward | yes |
| Per-cell drawdown halt | owner-set; **default −20%** | yes |
| Book drawdown halt | **default −15%** | — |
| Exitability depth multiple `k` | TBD (set at first universe build) | yes |
| DSR / PBO cutoffs | TBD (set at Gate-1 build) | — |
| Kelly fraction | TBD (start ~0.25, tune) | yes |

---

---

## 11. Amendment v0.2 (2026-06-28) — pressure-test fixes + seam closures

**Pressure test (clauses that did not survive scrutiny, now fixed):**

- **A. The log score explodes at the tails — exactly where we trade.** `log(q)` blows up as `q → 0/1`, and the favorite-longshot fade lives there. Fix: clip `p, q` to `[ε, 1−ε]` (ε = 0.01); **`EV_net` is the primary gate, `S` is a skill diagnostic only**; over-confident tail forecasts are explicitly penalised in calibration scoring. No cell is promoted on `S` alone.
- **B. ~50 outcomes is too few to detect a small edge — and the long tail may not produce them fast.** Fix: the Gate-4 bar is a **floor for moderate effect sizes, not a fixed rule**. Use **sequential testing (SPRT / always-valid e-values)** for early stop — a large measured edge graduates on fewer samples, a marginal one needs more. Gain power by **hierarchical pooling** of evidence across cells within an archetype (partial-pooling / shrinkage), so sparse cells borrow strength.
- **C. An unbounded swarm makes deflation impossible (nothing ever passes).** Fix: search is **budgeted** — a hypothesis quota per archetype and **pre-registered hypothesis families**, so the trial count stays finite and meaningful. Quality-controlled generation, not infinite monkeys.
- **D. "Beat the price" is meaningless if the price is stale.** On illiquid markets `q` may be a dead quote. Fix: `q` is a valid baseline **only with recent two-sided price formation**; otherwise treat as "no reliable prior" and score against our own base-rate prior with a widened safety margin.
- **E. Reflexivity.** Our own order moves a thin book. Fix: fills **walk the book** (assume market impact); displayed-price fills are forbidden, consistent with §3.
- **F. The decay gate can demote on noise.** Fix: Gate 7 fires only on a **statistically significant** edge degradation (its own change-point test), never on a normal drawdown.

**Seam 1 closed — insider/toxicity detection (§4.3).** Defined as a **counterparty-toxicity score**, composite of: (a) the classic insider signature — new wallet, single large one-sided bet, no history (the AlphaRaccoon pattern); (b) sharp price move with no public news (information asymmetry); (c) order-flow toxicity (which side informed flow is hitting); (d) a wallet's "market moved their way right after" hit-rate on low-liquidity markets. Above threshold → exclude or stand down. **Starts crude** (rules a+b from the public Data API), matures to c+d. Dual-use: the *same* signal, inverted, is the smart-money-convergence indicator — one data pipeline, both jobs.

**Seam 2 closed — portfolio correlation (§5/Gate 5).** A full cross-archetype correlation matrix is un-estimable from sparse resolved data. Fix: a **factor model** (Barra-style). The classifier assigns each market a small set of **factor loadings** at `t₀` (shared underlying/event, region-and-day for weather, league/sport, crypto-beta, a macro/sentiment factor) — cheap, prior-based, needs no history. Correlation is computed from **shared loadings**, not pairwise history. Until the factor model matures, Gate 5 degrades to **conservative per-cluster exposure caps** (already in §7).

*End of Constitution v0.2. Amendments append below; the kernel (§8) is sealed.*
