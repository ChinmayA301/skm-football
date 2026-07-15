# Project status

**Current release:** v0.1.0 — SKM-Chance (action-level proxy)  
**Next major milestone:** moment-based unified `skm_per90` ([roadmap](docs/ROADMAP.md))

## Completed

### Data & pipeline
- StatsBomb ingest and event features (Bundesliga 2023/24 open sample, 34 matches)
- `skm-build-events` → `events.parquet`
- `skm-build-scores` → `actions_scored.parquet`, `player_leaderboard.parquet`

### Models (v1)
- VAEP ΔP via sklearn fallback
- Difficulty (D), context (C), role (R), xT side column
- SKM combine: `SKM_i = ΔP_i × (1 + 0.3·D + 0.3·C + 0.3·R)`

### Models (v1.5) — Adjusted SKM weighting layer
- `adjusted_skm = skm × position_w × role_w × game_state_w × sequence_w`
- Position priors from StatsBomb lineups (`src/skm/models/weights.py`)
- Role weight from role-cluster action rates; game-state leverage weight;
  sequence weight for chains ending in shots
- `adjusted_skm_per90` in leaderboard and dashboard
- Verified end-to-end on remote StatsBomb data (3-match run): 91% position
  coverage, all weights within clips

### Models (Phase 5) — Moment segmentation
- `skm-build-moments` → `moments.parquet`, `moment_players.parquet`
- Heuristic boundaries: team change, ≤20 s gaps, dead balls, 25-action cap
- Moment types: open_play / set_piece / transition (regain + forward progress)
- Per-player involvement shares (on-ball touch share)
- 34-match sample: 12,172 moments; 7.3% contain a shot; median 3 actions

### Models (Phase 5b) — Chance + control layers, moment credits
- `skm_control`: progressive / press-resistance / own-third-defense bonuses,
  priced in median-positive-ΔP units (defensive VAEP already inside ΔP)
- `moment_value` roll-up; player credit = `α·own + (1−α)·share·moment_value`
- `skm-build-credits` → `player_credits.parquet`, `player_skm_v2.parquet`
- Phase 6 targets: ρ(v2, ΔP)=0.940 ✅ (<0.99); ρ(v2, progressive)=−0.10 ❌ —
  sensitivity analysis in ROADMAP; tuning deferred to a larger sample

### Validation & UI
- `skm-validate` (Tiers 1–3), `skm-export-reports`
- Streamlit dashboard with validation tab
- External benchmarks CSV (FotMob BL 23/24)
- CI: pytest, ruff

### Documentation
- README, roadmap, market positioning, case studies, related work
- Public repository: [github.com/ChinmayA301/skm-football](https://github.com/ChinmayA301/skm-football)

## Planned

| Phase | Focus |
|-------|--------|
| 6 | Single public `skm_per90` from moment credits |
| 7 | Match-relative context (competition, pressure, lineups) |
| 8 | Counterfactual / tracking / optional AI layer |

See [docs/ROADMAP.md](docs/ROADMAP.md) for detail.

### Expanded sample + visuals (v0.2.0-dev)
- Multi-competition pipeline (`--competitions "Name:Season,…"`): 216 matches
  across Bundesliga 23/24, WC 2022, Euro 2024, Ligue 1 22/23, La Liga 20/21 —
  487,561 scored actions, 233 players ≥400 actions (was 18)
- Phase 6 checks on expanded sample: ρ(v2, ΔP)=0.964 ✅; ρ(v2, progressive)
  =−0.19 ❌ (structural, see ROADMAP)
- Dashboard: Moments tab (moment map, top moments, v1↔v2 movers)
- `skm-export-replay`: self-contained HTML match replay with live SKM
  overlays + optional local-video sync (no footage bundled)
- `player_names.parquet` from lineups (names beyond the Bundesliga slice)

### Video intelligence (Layer 3, Stage 1)
- `skm-build-360`: StatsBomb 360 defender geometry → `D_360`, `skm_360`
- Coverage 216/216 games; held-out AUC for completion model
  0.690 (event-only) → **0.829** (with geometry)
- Expert-preference calibration scaffold (`preference.py`, Bradley-Terry)
  and staged CV/RL plan in `docs/VIDEO_INTELLIGENCE.md`
- Gate 2 passed (`scripts/propagate_d360.py`): D_360 through the full
  stack — ρ=0.995 overall but systematic movement (congestion mids up:
  Schick +55, Gündoğan, Mac Allister, Rodri; space-receiving wide players
  down: Carrasco, Doku, Ziyech)
- Dashboard "Label moments" tab collects expert preference pairs into
  `data/external/expert_moment_labels.csv` (ships header-only)
- **D_360 promoted** to the default difficulty (pipeline attaches 360 by
  default; `--skip-360` opts out; event-only D kept as `D_event`)

### Phase 6 — position-normalized SKM (v3)
- `skm-build-phase6` → `player_skm_v3.parquet`: z-score of v2 per-90
  within primary position group
- **Both Phase 6 targets pass**: ρ(v3, ΔP)=0.868 (<0.99 ✅);
  ρ(v3, progressive)=+0.061 (>0 ✅, flipped from −0.208)
- v3 is dimensionless (peer-relative); cross-position magnitudes → v2

## Notes

- Processed data and reports are local-only (see `.gitignore`); clone the repo and run the pipeline to generate them.
- Full-sample scoring: `./scripts/run_full_phase2.sh`
