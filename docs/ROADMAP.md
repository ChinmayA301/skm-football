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

## Phase 5 — Moment segmentation

**Goal:** Unit of account = `moment_id`, not a single action.

| Deliverable | Description |
|-------------|-------------|
| `src/skm/models/moments.py` | Possession phases, transitions, length caps |
| `moments.parquet` | Boundaries + context at moment start |
| `moment_players.parquet` | Involvement shares per player |

**Success criterion:** Same player, different matches → different moment portfolios.

---

## Phase 5b — Chance + control layers

| Layer | Role |
|-------|------|
| `skm_chance` | Current v1 formula (ΔP × DCR) |
| `skm_control` | Defensive VAEP + progressive/pressure/zone boost |

Actions roll up into `moment_value` during migration.

---

## Phase 6 — Unified SKM

**Goal:** Public `skm_per90` = sum of **moment credits**, tuned so:

- ρ(skm, progressive_per90) **> 0**
- ρ(skm, goals+xG) moderate (not a finisher clone)
- ρ(skm, ΔP) **< 0.99**
- Structural mids (e.g. Xhaka) rank higher than in v1

**Validation:** Scout comparison study, moment clip review, extended correlation tiers.

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
