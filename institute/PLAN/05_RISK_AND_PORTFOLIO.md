# 05 — Risk & Portfolio Management

**Status:** PLANNING ONLY. No build authorized.
**Scope:** Sizing discipline and ruin-avoidance for small personal capital ($100s–low $1000s) on Polymarket.

---

## 1. The Governing Principle

At small size, **market impact is negligible**. A $200 order in a market with $200k liquidity moves nothing. The only enemy is ruin. Every rule in this document exists to make ruin structurally impossible — not merely unlikely.

The corollary: do not over-engineer capacity (fill rates, market impact models, slippage budgets). Do engineer against the tail: a run of correlated losses, a coding bug that fires twice, an edge that was never real.

---

## 2. Fractional Kelly Sizing

### 2.1 The Kelly Formula

For a binary market (WIN = payoff b per $1 risked, LOSE = lose stake):

```
f* = p - (1 - p) / b
```

Where `p` is the Institute's model probability and `b = (1 / ask_price) - 1` is the payoff at the current ask. If `f*` ≤ 0, there is no edge — do not bet.

Full Kelly maximises long-run log-wealth growth but produces extreme variance: a 50% bankroll drawdown is expected ~13% of the time even with genuine edge. At small capital this variance is psychologically and operationally crushing.

### 2.2 Why Quarter-Kelly

The Institute uses **KELLY_FRACTION = 0.25**:

```
f = f* × 0.25 × calibration_quality
```

Rationale:
- **Edge uncertainty is real.** Every probability estimate carries model error. Full Kelly is only optimal when p is exactly right; it over-bets systematically when p is over-estimated. Quarter-Kelly is robust to moderate over-estimation.
- **Calibration is immature.** Until a cell has n ≥ 50 settled markets (Gate 4) with positive EV, `calibration_quality` shrinks the bet proportionally — a new cell can score near zero even if raw Kelly is positive.
- **Half-Kelly captures ~75% of log-growth at ~25% the variance.** Quarter-Kelly accepts ~56% of log-growth for ~6% the variance of full Kelly. At sub-$1000 bankroll, growth rate matters less than avoiding the "can't reload" scenario.
- **Multiple simultaneous positions.** When 5–10 cells are open, the combined portfolio Kelly is lower than any single-bet Kelly. Quarter-Kelly per cell is appropriate for a diversified book.

### 2.3 Calibration Quality Multiplier

```python
calibration_quality = min(1.0, max(0.0, mean_S / CALIB_TARGET))
# CALIB_TARGET = 0.05 (the proven weather-bot skill level)
```

A cell with zero or negative mean_S gets calibration_quality = 0 — it is cut, not merely sized down. This enforces the "bet only where proven" principle at the allocation layer.

---

## 3. The Cap Cascade

Four nested caps prevent any single bet, cluster, or theme from dominating. Applied in order (each acts on the output of the previous):

| Layer | Parameter | Value | What it prevents |
|---|---|---|---|
| **Cell cap** | `CELL_CAP` | 10% bankroll | Single-market concentration |
| **Cluster cap** | `CLUSTER_CAP` | 25% bankroll | Correlated-outcome concentration |
| **Archetype cap** | `ARCHETYPE_CAP` | 25% bankroll | Theme concentration (e.g. all weather) |
| **Total cap** | `TOTAL_CAP` | 60% bankroll | Ensures ≥40% cash reserve at all times |

### 3.1 Correlation Clustering

Cells are grouped when their archetype feature vectors have cosine correlation ≥ 0.50. Same-archetype cells always cluster (correlation = 1.0). The union-find algorithm in `allocator.py` handles transitive grouping.

Within a cluster, the **marginal-contribution gate (Gate 5)** enforces that non-anchor cells must contribute `ev_net ≥ 0.5 × anchor_ev`. Dominated cells are marked `gate5_wait`, not just undersized — they get zero dollars until the spread widens.

### 3.2 Reserve

The 40%+ cash reserve (bankroll × (1 - TOTAL_CAP)) is not idle. It serves:
1. **Dry powder** for high-conviction opportunities that appear during a drawdown.
2. **Psychological buffer** — operating with 60% deployed feels stable; 95% deployed forces panic decisions.
3. **Reload capacity** — if the book hits a drawdown halt, the reserve allows a controlled wind-down rather than forced liquidation.

---

## 4. Drawdown Halts

Two-level system. Both are hard stops — no overrides without explicit sign-off.

### 4.1 Per-Cell Halt

```
DEFAULT_CELL_DD = -0.20  (20% drawdown vs cell's peak NAV)
```

Triggered per-position by the decay detector (Gate 7). When a cell's pnl stream shows statistically significant edge erosion (Welch-z, alpha=0.05, material = recent_ev ≤ 0 or < 0.5 × early_ev), it is demoted to `gate7_watch`. No new bets are placed in that cell. Existing open positions run to settlement.

### 4.2 Book-Level Halt

```
DEFAULT_BOOK_DD = -0.15  (15% drawdown vs book peak)
```

Triggered at the portfolio level regardless of which cells are moving. When the book's total NAV falls 15% from its high-water mark:
- No new positions opened in any cell.
- Existing positions run to settlement (no forced exits — Polymarket positions are illiquid intra-day).
- Halt lifts only after human review + explicit sign-off.

### 4.3 Why 15% Book / 20% Cell

- **15% book halt** is aggressive for small capital. With $500 bankroll, this fires at -$75. That stings but does not end the operation. It forces a review before a losing streak can compound.
- **20% cell halt** is looser at the cell level to allow normal variance, but the statistical gate (Welch-z) means it only fires when the erosion is real, not noise.
- Both thresholds are tunable in `allocator.py` constants.

---

## 5. The 7-Gate Capital-Activation Ladder

No strategy touches real money until it has survived all seven gates in sequence. Gates are not a checklist — failure at any gate resets the strategy to `accumulating` status.

| Gate | Name | What it requires | Where implemented |
|---|---|---|---|
| **1** | Statistical | Brier / calibration score vs baseline on historical data; p < 0.05 | scoring module |
| **2** | Mechanism | Human-readable causal story for WHY the edge exists; no black boxes | DECISIONS_LOG |
| **3** | Red-team | Adversarial challenge: assume the edge is spurious; find the most plausible alternative explanation | manual review |
| **4** | Forward lockbox | n ≥ 50 settled OOS markets OR SPRT accept_H1; minimum 4-week span; positive EV | `gate4.py` |
| **5** | Portfolio | Marginal contribution within cluster ≥ 0.5× anchor; Kelly > 0 after correlation adjustment | `allocator.py` |
| **6** | Capital | Passes all size and drawdown constraints at the proposed allocation | `allocator.py` |
| **7** | Decay monitor | Welch-z early-vs-recent EV not significantly degraded | `decay.py` |

### 5.1 Paper → Forward Lockbox → Micro → Scale

The activation ladder maps to four operational tiers:

**Paper** (current): Simulated positions, zero real money. Accumulates Gate 4 evidence. The GCP VM runs this continuously.

**Forward Lockbox**: A cell graduates Gate 4. Capital is ring-fenced ("locked in a box") — committed in principle but not yet deployed. Human reviews Gate 3 (mechanism check). Explicit sign-off required to proceed.

**Micro**: Deploy at 10% of normal allocation. This is the first real money. Monitor for 2–4 weeks. Gate 7 runs continuously. If decay detected → return to Forward Lockbox. If no decay → proceed to Scale.

**Scale**: Normal allocation per the cap cascade. Gate 7 continues; a decay signal at any point drops the cell back to Forward Lockbox.

There is no automated escalation between tiers. Each promotion requires the user's explicit instruction.

---

## 6. Bankroll Management at Small Size

### 6.1 Starting Bankroll

Design assumption: $200–$1000 initial capital. At these sizes:

- **Minimum meaningful bet** is ~$5 (below this, fees consume edge). With CELL_CAP = 10% and $200 bankroll, maximum per-bet is $20 — this is not a constraint, it is correct sizing.
- **Minimum for diversification**: to run 3+ cells simultaneously with meaningful dollar amounts, bankroll should be ≥$300. Below that, run 1–2 cells only.
- **Do not fractionate below $5/bet**. If the Kelly sizing produces < $5, skip the market.

### 6.2 Reload Policy

The Institute does not auto-reload. If bankroll falls to reload threshold (default: 50% of starting capital), halt all activity and review before adding capital. Adding capital to a losing system is the most common amateur mistake.

### 6.3 Compounding

Bankroll is revalued daily (settled PnL + open mark-to-market). Kelly sizes update automatically because they are computed as a fraction of current bankroll. This means position sizes shrink naturally during drawdowns (de-risking) and grow during winning runs (compounding). No manual re-sizing needed.

### 6.4 Market Impact

Negligible at this scale. A $50 limit order in a market with $10k daily volume is ~0.5% participation. Do not model impact. Do check the order book depth before sending — if best bid/ask size is less than your intended order, you may get partial fill or need to walk the book.

---

## 7. The Real-Money Cord

**This is the hardest constraint in the Institute.**

The system is fake-money until:
1. At least one cell has cleared all 7 gates.
2. The user has reviewed the cell's Gate 3 (mechanism) documentation.
3. The user explicitly signs off in writing (message in the session or `99_DECISIONS_LOG.md` entry).

No automated system component may escalate from paper to real money. The cord is cut by the user, not the machine. The agent may flag when a cell approaches graduation, but may not act on it.

**Why explicit sign-off and not automation?**
- Legal and regulatory risk is on the user. They must own the decision.
- The system may have latent bugs untested with real money (e.g. order placement, settlement, wallet state).
- VPN/geo risk (see `06_EXECUTION_VENUE.md`) must be re-assessed at deployment time.
- Psychology changes with real money. The user should experience the paper run first, review it, and enter live with eyes open.

---

## 8. Parameters Summary

All tunable in `allocator.py` constants block:

| Parameter | Current Value | Range | Notes |
|---|---|---|---|
| `KELLY_FRACTION` | 0.25 | 0.10–0.50 | Start at 0.25; only increase after 100+ settled markets |
| `CELL_CAP` | 10% | 5–15% | Hard ceiling per market |
| `CLUSTER_CAP` | 25% | 15–35% | Correlated group max |
| `ARCHETYPE_CAP` | 25% | 15–35% | Theme max |
| `TOTAL_CAP` | 60% | 40–70% | Deployed max; inverse is reserve floor |
| `DEFAULT_CELL_DD` | -20% | -10 to -30% | Per-cell drawdown halt |
| `DEFAULT_BOOK_DD` | -15% | -10 to -20% | Portfolio halt |
| `CALIB_TARGET` | 0.05 | 0.03–0.10 | mean_S at which calib_quality = 1.0 |
| `MARGINAL_FLOOR_FRAC` | 0.50 | 0.30–0.70 | Non-anchor marginal EV floor |

Do not change multiple parameters simultaneously. Change one, run forward for 50+ markets, observe. Treat parameter changes as a strategy change requiring re-entry to Gate 4.

---

## 9. What This Does Not Cover

- **Liquidity / capacity modeling**: irrelevant at this size.
- **Tax treatment**: outside scope; user should consult an adviser.
- **Multi-venue correlation**: currently Polymarket-only; expand only if a second venue is added.
- **Options / synthetic structures**: not available on Polymarket; N/A.
