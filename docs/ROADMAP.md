# Roadmap

SKM's public number will keep evolving from an **action-level** proxy
toward a **moment-based**, position-fair `skm_per90`. This page is the
high-level vision; see [RESULTS.md](RESULTS.md) for what's validated so far.

## Vision

Football is a sequence of moments — short episodes where pressure,
scoreline, and team objectives shift. Players should be credited for
**involvement in successful moments**, not only for touching the ball.

```
StatsBomb events → moment segmentation → chance + control value
                 → player credit shares → position-normalized SKM
```

## Where things stand

v1–v3 are the **value-construction pipeline**; **v4 competence is the
headline metric** that finally delivers the founding thesis (position
competence, not attacking intent), and **v5 layers decisive-action and
pressure context on top of it**.

| Layer | Role | What it does |
|---|---|---|
| **v1 — SKM-Chance** | value pipeline | Action-level: VAEP ΔP weighted by difficulty, context, role |
| **v1.5 — Adjusted SKM** | value pipeline | + position, role, game-state, and sequence weights |
| **Moments / v2 credits** | value pipeline | Segment matches; roll value up per moment; share across involved players |
| **v3 — Position-normalized** | value pipeline | Players compared to positional peers, not the whole league |
| **360 geometry** | value pipeline | Real defender positions (StatsBomb 360) refit the difficulty model |
| **v4 — Competence (BASE)** | **headline** | Each action scored vs positional-peer expectation for that type. Decoupled from goals+assists (ρ≈−0.01); surfaces Van Dijk, Rüdiger, Kanté with zero output |
| **v5 — Contextual layers** | **on v4** | Context-weighted decisive actions (goals/assists/saves/line-breaks/tackles — low-xG & comeback/late/result-swinging weighted up) + a press-breaking component |

Full validation numbers: [RESULTS.md](RESULTS.md).

## v5 — what's built now, and what's honestly approximate

Built on event data (`skm.models.contextual`, `skm-build-v5`):
- **Difficulty-weighted decisive actions**: a low-xG goal outweighs a
  high-xG tap-in; a save scales with the shot xG faced. A validated example:
  a low-xG late comeback winner scores **6×** a high-xG blowout tap-in.
- **Game-state leverage**: comeback / final-minutes / result-swinging
  actions weighted up, garbage time down.
- **Press-breaking**: successful retention/progression under pressure,
  scaled by 360 defender distance.

Result on the 216-match sample: ρ(v5, goals) ≈ **−0.07** (decisive actions
rewarded heavily but *within context*, not by raw output); top-40 spans
every position with centre-backs leading.

**Honestly approximate (hand-set or proxied, disclosed):** the blend weights
are hand-set, not fitted; xG/assist are joined by (match, player, minute)
because the flattened events dropped the event id; "led to the win" is a
proxy (acted while not ahead, late, team won), not true causal attribution.

## The end goal — a live-video organic pipeline (future, honestly scoped)

The truthful version of SKM breaks **frames / live video into SKM-specific
"moment frames"** and generates every data point *organically* from the
video, rather than approximating context from event feeds. The CV pilot
(`skm.video`, [CV_PILOT.md](CV_PILOT.md)) is stage 1 of this and is **not**
production-ready (broadcast pans break single-frame calibration; ball
detection is weak — see the honest run write-up). Anything that can't be
done cleanly on event data (true causal chains, continuous pressure
geometry, off-ball chance creation) is scoped **here**, not faked in the
current metric.

## Also next

- **Expert calibration** (pairwise moment preferences) — scaffolded, needs
  real labels.
- **Fitted blend weights** for v5 once a validation target (expert labels or
  a scout study) exists — today's weights are deliberate priors.

## Related documents

- [RESULTS.md](RESULTS.md) — validated findings and headline numbers
- [SKM_MARKET_POSITIONING.md](SKM_MARKET_POSITIONING.md) — what SKM can and can't claim
- [CASE_STUDIES.md](CASE_STUDIES.md) — example players
- [RELATED_WORK.md](RELATED_WORK.md) — VAEP, xT, and related frameworks
- [WORKED_EXAMPLE.md](WORKED_EXAMPLE.md) — one real action, fully decomposed
