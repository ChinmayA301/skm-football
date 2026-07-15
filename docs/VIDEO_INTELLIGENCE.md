# Video Intelligence → Moment Metrics: Staged Architecture

Can SKM run a video-ingestion → moment-metric pipeline instead of relying
only on event data? **Yes — in stages, each of which must earn its keep on
real data before the next.** This document is the honest capability map.

```
Stage 1 (SHIPPED)   StatsBomb 360 freeze frames → pressure geometry → D_360
Stage 2 (PILOT)     User video → CV tracking → clock-synced context features
Stage 3 (SCAFFOLD)  Expert pairwise preferences → reward model → calibration
```

---

## Stage 1 — 360 freeze frames (shipped: `skm-build-360`)

StatsBomb 360 *is* video intelligence: player positions extracted from
broadcast frames at each event, quality-controlled and licensed. Open-data
360 releases turned out to cover **all 216 matches in our sample** (WC 2022,
Euro 2024, Bundesliga 23/24, Ligue 1 22/23, and the La Liga 20/21 release).

Per event we compute: `nearest_def_m`, `n_def_5m`, `n_def_10m`,
`n_def_ahead`, `n_visible` (see `src/skm/models/freeze_frame.py`), then
refit the completion-difficulty model with real defender geometry → `D_360`
and `skm_360`.

**Full-run results (216 matches, 372,657 covered on-ball actions):**

| Check | Value |
|---|---|
| Event coverage | 216/216 games |
| coef(nearest_def_m) | +0.99 (space → success, correct sign) |
| corr(D, D_360) | 0.58 — geometry ≠ the binary `under_pressure` flag |
| Covered actions with \|D_360 − D\| > 0.5 | 32.6% |
| **Held-out AUC (completion model), event-only** | **0.690** |
| **Held-out AUC with 360 geometry** | **0.829** (+0.14, 42 held-out games) |

The held-out AUC gap is the gate result: real defender geometry makes the
difficulty component substantially more accurate, not just different.

**Gate 2 — propagation review (`scripts/propagate_d360.py`):** replacing D
with D_360 across the full stack (ΔP/C/R/weights unchanged) keeps rankings
stable overall (ρ = 0.995, 233 players) but moves players *systematically*:
the biggest risers are congestion midfielders (Schick +55 ranks, Merino,
Griezmann, Gündoğan, Mac Allister, Çalhanoğlu, Rodri) and the biggest
fallers are wide players who receive in space (Carrasco −21, Doku −19,
Ziyech −15) — the event-only model had been over-crediting touchline
actions and under-crediting execution in central crowds. Outputs:
`player_leaderboard_360.parquet`, `player_skm_v2_360.parquet`. Phase 6
correlations are essentially unchanged (progressive re-pricing remains the
open Phase 6 problem).

**Limits (disclosed):** frames only show the camera's visible area
(`n_visible` tracks this); no player identities in frames; no continuous
tracking between events — off-ball runs are still invisible unless they
happen to be in frame at an event.

## Stage 2 — CV pilot on user-supplied video (design)

Production video→event extraction is a research-lab problem (SoccerNet
challenges exist precisely because it is unsolved at scale). What *is*
tractable as a pilot, on a clip the user owns:

1. **Detection**: YOLO-class model for players + ball per frame.
2. **Tracking**: ByteTrack/BoT-SORT for identity persistence.
3. **Homography**: pitch-line keypoints → map pixel coords to pitch coords
   (SoccerNet-Calibration baselines; broadcast pans need per-shot refits).
4. **Clock sync**: the replay tool (`skm-export-replay`) already syncs a
   local clip to the match clock by offset — the same join attaches CV
   tracks to event timestamps.
5. **Features**: the *same* geometry as Stage 1 (defender distances,
   density, lane occupancy) computed continuously rather than per event —
   plus what 360 cannot give: off-ball runs between events, pressing
   distances over time, team compactness curves.

**What it buys SKM:** continuous D inputs, off-ball involvement for moment
credits (the roadmap's "decoy runs" gap), pressing-moment detection.

**What it costs:** per-broadcast homography drift, occlusions, no ground
truth without labeled data. A pilot should validate against Stage 1: on a
360-covered match, CV-derived defender density at event times must agree
with freeze frames before any downstream use.

**Rule:** no CV-derived numbers enter published leaderboards until they
pass that agreement check. Demo ≠ measurement.

## Stage 3 — Expert takes as training signal (scaffolded: `preference.py`)

"Train on expert takes" has a trap: match ratings and pundit verdicts are
**outcome-biased** — the exact bias SKM exists to correct. Regressing SKM
onto FotMob ratings would just rebuild FotMob.

The honest design is **pairwise moment preferences**:

- Show an expert two moments (dashboard moment map / replay clips).
- Ask: *which mattered more?* — comparing situations, not stat lines.
- Learn a Bradley-Terry reward model over moment features
  (`fit_preference_model` in `src/skm/models/preference.py`; recovers
  ground-truth orderings on synthetic pairs, ρ > 0.9 in tests).

This is the supervised core of RLHF. The RL expansion on top, when label
volume justifies it: current weights (α, position priors, control
multipliers) become the *policy*; the preference reward model scores
proposed re-weightings; iterate. Until real labels exist, that loop is
design, not code — `data/external/expert_moment_labels.csv` is a
header-only template, deliberately unfilled.

**Label sources worth pursuing:** your own annotation sessions first
(cheap, immediate); then coaching-community sessions (each annotator
tagged, inter-rater agreement reported before any training run).

## Sequencing

| Step | Gate to proceed |
|---|---|
| 1. `skm-build-360` full run | ✅ **passed** — held-out AUC 0.690 → 0.829 |
| 2. Feed D_360 into skm/moments | ✅ **passed** — see below |
| 3. Collect ~200 expert pairs | inter-rater agreement > chance |
| 4. Preference-calibrate moment values | held-out pair accuracy > 0.65 |
| 5. CV pilot on one owned clip | agreement with 360 geometry at event times |
| 6. RL loop over weightings | only after 3–5 hold |
