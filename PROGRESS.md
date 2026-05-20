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
| 5 | Moment segmentation and player involvement |
| 5b | `skm_chance` + `skm_control` layers |
| 6 | Single public `skm_per90` from moment credits |
| 7 | Match-relative context (competition, pressure, lineups) |
| 8 | Counterfactual / tracking / optional AI layer |

See [docs/ROADMAP.md](docs/ROADMAP.md) for detail.

## Notes

- Processed data and reports are local-only (see `.gitignore`); clone the repo and run the pipeline to generate them.
- Full-sample scoring: `./scripts/run_full_phase2.sh`
