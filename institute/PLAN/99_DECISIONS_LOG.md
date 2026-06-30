# The Institute — Decisions Log (auditable; part of the moat)

Every material judgment call in the planning phase, with rationale + status. Open items
need user input before the relevant build phase.

## Locked decisions (user, 2026-06-30)
- **D1 Mandate:** personal autonomous Polymarket fund, paper -> real gated + sign-off.
  Not a product to sell.
- **D2 Cost:** free prototype; premium budget unlocked at live launch (~$350-460/mo).
- **D3 Scope:** all 4 market families in; cut un-edgeable sub-markets with reasons.
- **D4 Edge engines:** all 4 first-class, best-fit per market.
- **D5 Autonomy:** autonomous + self-improving on paper; real money gated + sign-off.
- **D6 Capital:** small personal ($100s-low $1000s), Polymarket via VPN.
- **D7 Runtime:** "best available" tooling, my call, justified.

## Planning judgment calls (made, with rationale)
- **J1 CUT crypto price-levels / FX / commodities / index levels.** Efficient (options-arb
  priced); counterparty is professionals. No retail crowd to beat. (01)
- **J2 Behavioral FLB is the universal baseline.** Most reliable confirmed edge (weather,
  sports, literature). Every vertical starts with it before adding quant/news/flow. (01,02)
- **J3 Copy-flow used as FADE as much as follow.** The $85M 2024-election whale shows large
  flow can DISTORT, not inform. Whale-detection is a contrarian signal too. (01,02)
- **J4 Plain-Python org now; LangGraph deferred.** Until single passes > 10 min or n>200
  markets, plain cadence.py + the llm seam is cheaper, simpler, offline-testable. (04)
- **J5 Gate pipeline code is NEVER self-modified.** Track-record integrity is the moat;
  self-mod is restricted to weights/strategies within guardrails (3-tier leash). (08,07)
- **J6 CPI 3rd-model fix = different INPUT variable (PPI/import prices), not a new window.**
  Genuine independence; detect failure via pairwise error corr > 0.7. (02)
- **J7 Net-of-fee edge is the bet test.** Re-rank/CUT any market whose edge < taker fee
  (0% geopolitics .. 1.8% crypto). (06,09)
- **J8 Real LLM provider (paid) deferred to Phase 1** and justified by the news engine;
  until then forecasting stays mock-gated (no placeholder burn on live markets). (04,09)
- **J9 Point-in-time honesty is absolute** — frozen priors, idempotent, never see outcome.
  This is both integrity AND the un-backfillable data moat. (03,07)

## OPEN items — need user input before the relevant phase
- **O1 (Gate G2) Sports sequencing.** You vetoed sports as the immediate build, but selected
  Sports in-scope. Research ranks soccer/World Cup + NBA props as Tier 1 by volume/edge.
  WHEN should sports enter — Phase 3 as planned, later, or never? Your call.
- **O2 (Gate G1) Phase 1 real-LLM spend.** Wiring a paid LLM provider is the first recurring
  real cost (~$2.26/50-mkt pass). Approve before B6.
- **O3 (Gate G3) Premium-data budget at launch.** ~$350-460/mo (Pinnacle, Bloomberg
  consensus, Nansen, HLTV). Approve the list + cap before live.
- **O4 (Gate G4) Real-money activation.** Hard manual gate. Never automated. Requires your
  co-sign per cell at the micro tier. Plus: acknowledge the AU/VPN ToS + forfeiture risk (06).
- **O5 Self-modification leash.** Confirm Tier A/B/C boundaries (08): how much autonomous
  strategy/weight change is allowed before a human digest/veto.

## Known limitations carried into the build (be honest)
- Macro verticals are MONTHLY cadence -> slow track record (inherent; accepted via depth-first).
- The institute's edge is unproven until real settled forward results accrue; all current
  numbers are backtest/paper. Gate 4 (lockbox) exists precisely to prevent over-trust.
- VPN execution is a Polymarket ToS violation with real forfeiture risk (06) — paper-only
  until the user explicitly, knowingly goes live.

## How to resume the build
Read 00_CHARTER -> 09_ROADMAP -> this log. Start at Phase 0 / B2. Each Bn follows the proven
Opus-spec -> Sonnet-build -> Opus-verify loop. The research (01-08) is the reference depth.
