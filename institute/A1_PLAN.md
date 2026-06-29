# A1 — Data Plane + Predictability-Map Skeleton (implementation plan)

*Serves [ARCHITECTURE.md](../ARCHITECTURE.md) milestone A1. Scope: `sensor → classify → corpus → resolve → map`. No predictors, no gates, no capital — A1's single deliverable is the **first predictability map**: where edge plausibly lives, measured with dumb baselines on resolved history. New `institute/` package; imports nothing from `desk/` yet, reuses `papertrader/lib` clients.*

## Layout
```
institute/
  __init__.py  README.md  config.json  cli.py
  sensor/    gamma.py  dataapi.py  snapshot.py
  classify/  archetype.py  factors.py  tradeability.py
  corpus/    schema.py  store.py  registry.py
  resolve/   pipeline.py
  map/       baselines.py  predictability.py
  tests/     (5 files, below)
  data/      (gitignored sqlite; jsonl is source of truth)
  conftest.py
```

## Schemas (`corpus/schema.py`, dataclasses)
- **Market** — id, slug, venue, question, archetype, end_date, resolution_source, raw_meta
- **ContextSnapshot** — market_id, t0, q_bid, q_ask (executable, not mid), book_depth, features{}, factor_loadings{}, toxicity_score, tradeable(bool)+reasons[]
- **Resolution** — market_id, resolved_at, y∈{0,1}, actual_value
- **Trial** — id, archetype, strategy_id, params, search_context, metrics{mean_S, EV_net, n, DSR, PBO}, verdict, ts  *(registry skeleton; populated in A2)*
- **MapCell** — archetype, baseline, n, win%, mean_S, EV_net, naive_ROI, status∈{green,grey,red}

## Components
- **sensor/gamma.py, dataapi.py** — reuse `papertrader/lib/polymarket.py` (Gamma client + clobTokenIds double-parse). Add Data API reads (`/trades`,`/holders`) for depth + toxicity inputs. Public, no key.
- **sensor/snapshot.py** — capture context@t0; record executable q (bid/ask), depth. Forbid post-t0 features.
- **classify/archetype.py** — rules first (slug/question patterns), Haiku fallback for ambiguous. Output archetype tag.
- **classify/factors.py** — assign cheap prior-based factor loadings (shared event, region-day, league, crypto-beta, macro) per CONSTITUTION §11 Seam 2.
- **classify/tradeability.py** — §4 precheck: resolvable + exitable (depth ≥ k×position, k=3 default) + recent two-sided price formation (else mark "no reliable prior") + crude toxicity flag (new-wallet-one-sided / price-move-no-news).
- **corpus/store.py** — append-only jsonl (source of truth) + rebuildable sqlite index. **registry.py** — trial log skeleton.
- **resolve/pipeline.py** — per-archetype ground truth. **A1 wires weather (reuse `papertrader/lib/settlement.py`) + crypto-daily-close (public price)**. Sports deferred to A3 (needs odds data).
- **map/baselines.py** — three nulls only: `price_follow` (sanity: must score ≈0 market-relative skill), `longshot_fade` (our proven NO-on-cheap-longshot mechanism), `base_rate`.
- **map/predictability.py** — score each baseline vs market on resolved history → MapCells → `data/predictability_map.json`. **This is A1's headline output.**
- **cli.py** — `institute scan | classify | resolve | map | status`.

## Tests (verify gate — A1 "done" =)
1. `test_archetype` — known markets classify correctly.
2. `test_tradeability` — stale-price & thin-depth markets rejected; healthy pass.
3. `test_baselines` — on synthetic data: `price_follow` mean_S ≈ 0 (copying the price is zero edge, per §2); `longshot_fade` mean_S > 0 on a longshot-biased synthetic set.
4. `test_store_roundtrip` — append + rebuild index byte-identical.
5. `test_map_smoke` — map runs end-to-end on weather resolved data; the `weather × longshot_fade` cell shows +EV consistent with the live +$68 we already observed (regression anchor to reality).
- All tests run from repo root (`conftest.py` carries over the papertrader sys.path fix).

## Config (`config.json`)
archetypes[], depth_multiple k=3, stale_price_window, ε=0.01, longshot_cap=0.35 (from the weather cap sweep).

## Out of scope (later milestones)
Strategy-gen, gates 1–7 logic, red-team, allocator, factor-model maths, sports data, real predictors. A1 is data plane + map only.

## Effort / sequence
sensor → schema/store → classify → resolve(weather first) → baselines → map → tests. Weather data already exists, so the first map can render almost immediately; crypto adds the second archetype to prove cross-domain.
