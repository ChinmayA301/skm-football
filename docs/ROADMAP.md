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

| Layer | What it does |
|---|---|
| **v1 — SKM-Chance** | Action-level: VAEP ΔP weighted by difficulty, context, role |
| **v1.5 — Adjusted SKM** | + position, role, game-state, and sequence weights |
| **Moments** | Matches segmented into possession phases, transitions, and set pieces |
| **v2 — Moment credits** | Value rolled up per moment and shared across involved players |
| **v3 — Position-normalized** | Players compared to positional peers, not the whole league |
| **360 geometry (Stage 1 video intelligence)** | Real defender positions from StatsBomb 360 refit the difficulty model |

Full validation numbers: [RESULTS.md](RESULTS.md).

## What's next

- **Deeper video intelligence.** A CV pilot (detection + tracking +
  homography on user-owned clips) is designed but gated: any camera-derived
  number must agree with StatsBomb 360 ground truth before it's trusted.
- **Expert calibration.** A pairwise moment-preference model is scaffolded
  — the honest way to bring in expert judgment without reintroducing the
  outcome bias SKM is built to correct. It needs real labeled comparisons.
- **Off-ball credit.** Pressing and decoy-run involvement aren't captured
  yet; StatsBomb 360 only samples positions at event time.
- **Match-relative context.** Competition stage (league vs. knockout),
  finer scoreline/minute curves, lineup presence for low-touch defenders.

## Related documents

- [RESULTS.md](RESULTS.md) — validated findings and headline numbers
- [SKM_MARKET_POSITIONING.md](SKM_MARKET_POSITIONING.md) — what SKM can and can't claim
- [CASE_STUDIES.md](CASE_STUDIES.md) — example players
- [RELATED_WORK.md](RELATED_WORK.md) — VAEP, xT, and related frameworks
- [WORKED_EXAMPLE.md](WORKED_EXAMPLE.md) — one real action, fully decomposed
