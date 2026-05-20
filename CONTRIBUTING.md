# Contributing

Thanks for your interest in SKM. This guide covers local setup, tests, and where to read more.

## Setup

```bash
git clone https://github.com/ChinmayA301/skm-football.git
cd skm-football
./scripts/setup_venv.sh
source .venv/bin/activate
pip install -e ".[dev,model,app]"
```

If `scipy` fails to build, use binary wheels (see README troubleshooting).

## Run the pipeline

```bash
skm-build-events --max-matches 3   # quick test
skm-build-scores --max-games 5

# full open sample
./scripts/run_full_phase2.sh
```

## Tests and lint

```bash
pytest
ruff check src tests
```

## Validation and dashboard

```bash
skm-validate
skm-export-reports
streamlit run app/streamlit_app.py
```

Reports are written to `data/reports/` (gitignored).

## Further reading

- [docs/ROADMAP.md](docs/ROADMAP.md) — planned work
- [docs/SKM_MARKET_POSITIONING.md](docs/SKM_MARKET_POSITIONING.md) — metric claims and limits
- [docs/CASE_STUDIES.md](docs/CASE_STUDIES.md) — example validation narratives
- [PROGRESS.md](PROGRESS.md) — current status

## External benchmarks

Tier 3 validation merges [`data/external/bundesliga_2324_benchmarks.csv`](data/external/bundesliga_2324_benchmarks.csv). Add rows with `player_name` and rating columns, then re-run `skm-validate`.
