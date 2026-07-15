# Roadmap

SKM v1 is an **action-level** process metric. The public headline number will evolve into a **moment-based**, match-relative **`skm_per90`**—still one metric, with explainability columns behind it.

---

## Vision

Football is a sequence of **moments**: short episodes where pressure, scoreline, and team objectives shift. Players should be credited for **involvement in successful moments**—not only ball touches.

**Target pipeline:**

1. Segment the match into moments (possessions, transitions, pressing phases).
2. Score each moment for team success in **that match context**.
3. Allocate credit to involved players (carrier, recipient, presser when observable).
4. Aggregate to **one SKM per 90**—distinct from raw goals/assists or reputation ratings.

See [SKM_MARKET_POSITIONING.md](SKM_MARKET_POSITIONING.md) for claims and limitations.

---

## v1 (released) — SKM-Chance

| Component | Status |
|-----------|--------|
| StatsBomb ingest + event features | Done |
| VAEP ΔP (sklearn) | Done |
| Difficulty **D**, context **C**, role **R** | Done |
| xT column + hidden-influence views | Done |
| Streamlit dashboard + validation CLI | Done |
| Tier 1–3 validation + FotMob benchmarks CSV | Done |
| Bundesliga 2023/24 open sample (34 matches) | Done |

```text
SKM_i = ΔP_i × (1 + 0.3·D_i + 0.3·C_i + 0.3·R_i)
```

**Known limits:**

- Isolated ball actions, not full moments.
- ρ(skm, ΔP) ≈ 0.996 on the open sample; D/C/R add little so far.
- ρ(skm, progressive_per90) ≈ −0.11 — mids under-rewarded vs attack-leaning actions.
- 34-match sample, not full season.

---

## v1.5 (released) — Adjusted SKM weighting layer

```text
adjusted_skm = skm × position_weight × role_weight × game_state_weight × sequence_weight
```

| Component | Status |
|-----------|--------|
| Position priors (StatsBomb lineups → position groups × SPADL types) | Done |
| Role weight from role-cluster action rates | Done |
| Game-state leverage weight (garbage time / late close) | Done |
| Sequence weight (chains ending in shots share credit) | Done |
| `adjusted_skm_per90` in leaderboard + dashboard | Done |

**Known limits:** position weights are hand-set priors; sequence chains are a
heuristic (same team, ≤15 s gaps), not tracked possessions; partial overlap
between game-state weight and C. All weights are clipped to modest ranges so
adjusted SKM stays close to base SKM until the priors are validated.

---

## Phase 5 (released) — Moment segmentation

**Goal:** Unit of account = `moment_id`, not a single action.

| Deliverable | Status |
|-------------|--------|
| `src/skm/models/moments.py` — possession phases, transitions, set pieces, length caps | Done |
| `moments.parquet` — boundaries + start context (score, minute, reason, type) | Done |
| `moment_players.parquet` — per-player involvement shares | Done |
| `skm-build-moments` CLI | Done |

On the open 34-match sample: 12,172 moments (66.6% open play, 21.6% set
piece, 11.8% transition), 7.3% containing a shot, median 3 actions per moment.

**Success criterion** (same player, different matches → different moment
portfolios): 53% of players show varying per-match moment counts on the
34-match sample.

**Known limits:** boundaries are heuristics (team change, ≤20 s gaps, dead
balls, 25-action cap), not StatsBomb possession chains; attack direction is
inferred from shot end locations; involvement is on-ball touch share only —
pressers and off-ball runners enter in Phase 7 when pressure events are
ingested.

---

## Phase 5b (released) — Chance + control layers, moment credits

| Layer | Role | Status |
|-------|------|--------|
| `skm_chance` | Current v1 formula (ΔP × DCR) | Done (alias of `skm`) |
| `skm_control` | Structural boost: progressive / press-resistance / own-third defense | Done |
| `moment_value` | Σ (skm + skm_control) per moment | Done |
| Player credits | `α·own_value + (1−α)·share·moment_value`, α=0.7 | Done |
| `skm-build-credits` CLI → `player_credits.parquet`, `player_skm_v2.parquet` | Provisional v2 leaderboard | Done |

**Correction to the original plan:** defensive VAEP already flows through ΔP
(`delta_p = offensive_value + defensive_value`), so `skm_control` is the
structural boost only — re-adding defensive VAEP would double count. Bonuses
are priced in units of the sample's median positive ΔP (self-calibrating).

**Phase 6 target status — expanded sample (216 matches / 5 competitions,
n=233 players ≥400 actions):**

| Target | v1 | v2 (α=0.7) | Met? |
|--------|----|-----------|------|
| ρ(skm, ΔP) < 0.99 | 0.996 | **0.964** | ✅ |
| ρ(skm, progressive_per90) > 0 | −0.125 | −0.194 | ❌ |

**Findings (disclosed, not tuned away):** on the expanded sample the negative
progressive correlation is a *structural* property, not small-n noise — both
v1 and v2 concentrate value in shot-adjacent actions, and moment sharing
amplifies it (touch-share redistribution favors attackers in shot-ending
moments). Sensitivity: lowering α worsens it; an 8× progressive bonus only
halves it. Phase 6 therefore needs a modeling change (per-position
normalization and/or moment-type value weighting), not parameter tuning —
the 233-player sample now makes that work defensible.

---

## Phase 6 (released) — Position-normalized SKM (v3)

**The structural fix** (pre-registered in Phase 5b findings, not tuned):
`skm_v3` = z-score of `skm_v2_per90` within the player's primary position
group (`skm-build-phase6` → `player_skm_v3.parquet`). Groups <8 players
fall back to a global z, flagged in `pos_z_basis`.

**Target status (233 players, geometry-aware D promoted):**

| Target | v2 raw | v3 position-normalized | Met? |
|--------|--------|------------------------|------|
| ρ(skm, ΔP) < 0.99 | 0.959 | **0.868** | ✅ |
| ρ(skm, progressive_per90) > 0 | −0.208 | **+0.061** | ✅ |

The progressive correlation flips sign — barely positive, honestly stated,
but the structural claim holds: v3 no longer punishes progressive volume,
because each position competes against its own peers. Position leaders are
face-valid (ball-playing CBs Young-Gwon Kim / Koulibaly / Orban; Freuler
top DM; Sommer top GK).

**Interpretation change (disclosed):** v3 is dimensionless — "how good
relative to positional peers", the question scouts ask — not a per-90
value quantity. Cross-position magnitude comparisons should use v2.

**Still open for Phase 6 completion:** scout comparison study, moment clip
review, expert preference calibration (labels pending).

---

## Phase 7 — Match-relative context

- Competition stage (league / cup / knockout)
- Pressure and ball-recovery events as involvement
- Lineup presence for low-touch contributors
- Finer scoreline and minute curves

---

## Phase 8 — Advanced layers (future)

| Priority | Approach |
|----------|----------|
| 1 | Counterfactual / option-set value |
| 2 | Scout-label residual (optional) |
| 3 | Moment sequence embeddings |
| 4 | Tracking data for off-ball |

Optional: `skm_trend` (year-on-year slope + age + minutes) as a separate potential signal—not raw SKM alone.

---

## Target architecture

```mermaid
flowchart LR
  Events[events.parquet]
  Moments[moments.parquet]
  Actions[skm_chance + skm_control]
  Credits[moment_player_credits]
  SKM[skm_per90 unified]
  Events --> Moments --> Actions --> Credits --> SKM
```

---

## Related documents

- [CASE_STUDIES.md](CASE_STUDIES.md) — example players
- [RELATED_WORK.md](RELATED_WORK.md) — VAEP, xT, positioning
- [PROGRESS.md](../PROGRESS.md) — implementation status
