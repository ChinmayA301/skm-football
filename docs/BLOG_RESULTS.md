# SKM: Real Results for the Blog Update

Draft material for updating the blog post ("Successful Key Moment") with
implemented results, per the build plan Phase 4. All numbers below are
reproducible from this repo (`skm-build-scores` → `skm-build-moments` →
`skm-build-credits` → `skm-validate`).

## What was built

- **Sample:** 216 matches / 487k scored actions across 5 competitions
  (Bundesliga 23/24, World Cup 2022, Euro 2024, Ligue 1 22/23, La Liga
  20/21), StatsBomb open data. 233 players with ≥400 actions.
- **v1 (SKM-Chance):** `SKM = ΔP × (1 + 0.3D + 0.3C + 0.3R)` — the exact
  formula from the build plan. ΔP = sklearn VAEP; D = inverse completion
  probability; C = minute/scoreline; R = role-cluster unusualness.
- **v1.5 (Adjusted SKM):** × position / role / game-state / sequence
  weights (modest, clipped, disclosed priors).
- **Phase 5/5b:** moment segmentation (~68k moments), moment credits, and
  a provisional v2 leaderboard (`α·own + (1−α)·share·moment_value`).
- **Tools:** Streamlit dashboard (leaderboard, timelines, moments, v1↔v2
  movers, validation) and an HTML match replay with live SKM overlays.

## Headline numbers (honest, not cherry-picked)

| Check | Value | Reading |
|---|---|---|
| ρ(SKM v1, ΔP) | 0.996 | v1 tracks VAEP closely — D/C/R adjust little at these weights |
| ρ(SKM v2, ΔP) | **0.959** | moment credits genuinely diverge from raw VAEP (target <0.99 ✅) |
| ρ(SKM v3, ΔP) | **0.868** | position-normalized v3 diverges further ✅ |
| ρ(SKM v1, xT) | 0.50 | SKM is not a ball-progression grid |
| ρ(SKM v1, assists/90) | 0.29 | not an assists clone |
| ρ(SKM v1, xG/90) | 0.18 | not a shooting-volume clone |
| ρ(SKM, progressive/90) | −0.21 (v2) → **+0.06 (v3)** | the sign flip — see finding 3 |
| ρ(SKM v1, FotMob rating) | −0.57 (n=11, BL only) | SKM disagrees with reputation ratings; sample tiny |
| Held-out AUC, completion model | 0.690 → **0.829** with 360 geometry | real defender positions beat the binary pressure flag |

## The findings worth writing about

**1. Moment sharing favors attackers (a real, structural result).**
The Phase 6 target ρ(SKM, progressive/90) > 0 fails on 233 players, and it
fails *worse* under moment sharing (−0.21 vs −0.07). Redistributing moment
value by touch share channels credit toward players present in shot-ending
moments. An 8× progressive bonus only halves the deficit. Conclusion:
progressive work must be re-priced structurally (per-position
normalization), not parameter-tuned. This is an honest negative result —
and it is what separates the project from marketing.

**3. The structural fix works: position normalization flips the sign.**
`skm_v3` (z-score within primary position group, pre-registered before
results were computed) passes both Phase 6 targets: ρ(v3, ΔP) = 0.868 and
ρ(v3, progressive) = +0.06 — barely positive, honestly stated, but the
metric no longer punishes progressive volume. Position leaders are
face-valid: ball-playing CBs (Young-Gwon Kim, Koulibaly, Orban), Freuler
top DM, Sommer top GK. v3 answers "how good vs positional peers" — the
scout's question — at the cost of cross-position magnitude comparisons.

**4. Real defender geometry beats the pressure flag.**
Refitting completion difficulty with StatsBomb 360 freeze-frame positions
lifts held-out AUC from 0.690 to 0.829. Propagated through the metric,
congestion midfielders rise (Gündoğan, Mac Allister, Rodri) and wide
players receiving in space fall (Doku, Carrasco) — the event-only model
had been over-crediting touchline actions.

**2. Shootout kicks are a VAEP landmine (found and fixed).**
Penalty-shootout actions (period 5) have no "next k actions", so VAEP
assigned ≈ −3.7 per shootout even to *scored* kicks — Ronaldo and Messi
were both docked nearly −4 SKM for winning shootouts. 65 such actions
carried −107 SKM. The pipeline now excludes period 5; after the fix Messi
enters the v2 top-10. Worth a paragraph in the blog as a worked example of
metric auditing.

## Player results (post-fix, v2 per-90, ≥400 actions)

Gakpo · Tella · Boniface · Mbappé · Saka · Mittelstädt · Young-Gwon Kim ·
Xavi Simons · Neymar · Messi — face-valid across competitions, with
Bundesliga "hidden heroes" (Tella, Boniface, Mittelstädt) surfacing beside
tournament stars.

## Figures (in `docs/assets/`)

1. `fig_v1_vs_v2.png` — v1 vs v2 per-90 diagonal; movers labeled.
2. `fig_position_fairness.png` — SKM v2 by position group; the attacking
   tilt is visible and disclosed (Phase 6 target).

## Worked example

See [WORKED_EXAMPLE.md](WORKED_EXAMPLE.md) — a real Kondogbia pass under
pressure (78', La Liga) vs a routine de Jong pass with near-identical ΔP,
with every component value from the actual model. Replaces the blog's
hypothetical example.

## Caveats to state in the blog

- Open event data only: D lacks defender geometry (Layer 3 pending).
- Estimated minutes (action-count proxy), not true minutes.
- Mixed club/tournament contexts in one sample.
- Tier 3 external benchmark covers 11 Bundesliga players only.
- v2 moment credits are provisional; Phase 6 (re-pricing progressive
  work) is explicitly open.
