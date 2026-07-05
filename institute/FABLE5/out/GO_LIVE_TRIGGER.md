# GO_LIVE_TRIGGER — the paper → real-money evidence bar (per cell)

**Design intent:** this bar is the MINIMUM the machine must clear before real capital is
even discussable. The user co-sign sits ON TOP of it and is never removable. No automated
component may act on real money; the trigger produces a WORKSHEET, not an order.

## The bar — ALL of the following, per cell, per venue

### 1. Gate record (from the 7-gate spine, unmodified)
- Gates 1–7 passed, with Gate 4 = forward lockbox: SPRT accept-H1 on **net-of-all-costs
  ROI** (fee at the venue's actual schedule for the traded price points, ceil-rounded;
  measured spread from the F3 tape, not any haircut floor), over ≥4 calendar weeks,
  **computed per venue on the venue being funded — a pooled cross-venue graduation never
  funds a venue by itself; the funded venue's own sample must carry the SPRT** (the pooled
  result may inform the prior, not the decision).
- SPRT boundary is the only early exit, with one guard: a boundary hit at n far below the
  pre-registered expected-n is provisional pending Tier-B review (a mis-specified H1 makes
  boundaries reachable on luck — the review checks the H1 against realized variance).
- Survives its frozen family's e-BH correction (see ARCHITECTURE §4 A1). A cell that only
  passes uncorrected does not pass.

### 2. Forward-lockbox integrity audit (Opus 4.8, independent)
- Every lockbox forecast verified frozen-before-outcome (hash check against the append-only
  ledger), idempotent on replay, and computed from data available at decision time.
- Zero manual edits to the ledger in the cell's history. Any edit = restart lockbox.

### 3. Economic sanity
- Net edge per bet ≥ 2× the venue's all-in cost at the cell's typical price point. (This is
  DELIBERATELY stricter than the paper-stage §5 bars in ARCHITECTURE — the ladder is:
  study bar admits paper seeding; this bar admits money. A cell may live between the two
  bars indefinitely, on paper. That is a feature.)
- Projected 90-day net profit at the proposed allocation ≥ $50 [ASSUMPTION — user may
  re-set]: below this, real-money operation isn't worth its risk/attention overhead.
- Kelly sizing at the estimated edge, quarter-Kelly, cap cascade, produces bets ≥ $5.

### 4. Venue-risk acknowledgement (the part the machine cannot certify)
The worksheet must show, and the user must initial, each of:
- **Forfeiture exposure:** venue balance cap requested, worst case = 100% loss of that
  balance (A2 status: CANNOT CERTIFY — p_detect has no empirical basis; the user is
  accepting an unquantified tail, and the worksheet says so in those words).
- **Jurisdiction reality:** AU is restricted on BOTH venues (Kalshi restricted list; PM
  ToS §2.1.4). Real-money access route, whose account, and whose legal exposure are the
  user's decisions — the Institute never automates or advises circumvention.
- **Oracle/resolution tail (PM):** UMA disputes 1,150+ YTD 2026; capital can freeze 4–7
  days or resolve wrongly; max 10% of bankroll in markets sharing one resolution event.
- **Ruin restatement:** joint worst case (venue forfeiture + correlated trading loss)
  = −45% at design caps; +82% required to recover; occurs at most once (A4 rule).

### 5. Operational readiness
- Kill switch (`LIVE_TRADING_ENABLED`) verified working by a dry-run drill.
- Daily loss cap wired and tested. Book halt −15% tested on synthetic data.
- Micro-tier only: first real allocation = 10% of the cell's normal size for ≥2 weeks and
  ≥20 settled bets before any promotion; every promotion is a fresh user sign-off.

## What can NEVER trigger go-live
- Backtest results alone (any n). Paper results that fail SPRT. A "great month". A cell
  whose kill threshold was moved after data. Any cell during an open book halt. Any
  venue while its A2 worksheet says CANNOT CERTIFY and the user has not signed that line.

## Standing order
If evidence and this document ever conflict, the stricter reading wins, and the conflict
is logged as an OPEN_DECISIONS item rather than resolved silently.
