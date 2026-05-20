# Contributing

No Homebrew required.

## Setup

```bash
./scripts/setup_venv.sh
source .venv/bin/activate
```

## Tests

```bash
pytest
ruff check src tests
```

## Validation (after Phase 2)

```bash
./scripts/run_full_phase2.sh   # full 34-match sample
skm-validate
skm-export-reports
streamlit run app/streamlit_app.py
```

Fill `data/external/bundesliga_2324_benchmarks.csv` for Tier 3 public-rating comparison.
See `docs/CASE_STUDIES.md` for blog narratives.

Regenerate `data/reports/` locally (`skm-validate && skm-export-reports`) before blog charts — reports are gitignored.

## Roadmap & positioning

- [docs/PICKUP.md](docs/PICKUP.md) — resume next session
- [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md) — v1 publish snapshot (local)
- [docs/COMPLETE_BUILD_PLAN.md](docs/COMPLETE_BUILD_PLAN.md) — master plan Phases 1–8 (local)
- [docs/ROADMAP.md](docs/ROADMAP.md) — Phases 5–8 (moments, unified SKM, AI)
- [docs/SKM_MARKET_POSITIONING.md](docs/SKM_MARKET_POSITIONING.md) — honest claims vs market stats

## GitHub

```bash
./scripts/publish_to_github.sh skm-football your-github-username
```

Create the repo at https://github.com/new then `git push -u origin main`.
