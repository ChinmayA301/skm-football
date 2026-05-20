# SKM — Skill-Key Moments

Open-source pipeline for **process-based player valuation** in football.

**SKM v1** scores every on-ball action with VAEP **ΔP** plus difficulty (**D**), context (**C**), and role (**R**). The long-term goal is a **moment-based** metric that credits players for involvement in match-winning phases—not only the ball carrier. See the [roadmap](docs/ROADMAP.md).

**v0.1.0** · Bundesliga 2023/24 (StatsBomb open, 34 matches) · sklearn VAEP

```
SKM_i = ΔP_i × (1 + 0.3·D_i + 0.3·C_i + 0.3·R_i)
```

Data: [StatsBomb open data](https://github.com/statsbomb/open-data) · Models: [socceraction](https://github.com/ML-KULeuven/socceraction) (VAEP, SPADL, xT)

---

## How it works

```mermaid
flowchart LR
  StatsBomb[StatsBomb_open_data]
  Events[events.parquet]
  VAEP[VAEP_deltaP]
  SKM[SKM_DCR_combine]
  Board[player_leaderboard]
  StatsBomb --> Events --> VAEP --> SKM --> Board
```

| Step | Command | Output |
|------|---------|--------|
| Ingest + features | `skm-build-events` | `data/processed/events.parquet` |
| VAEP + SKM | `skm-build-scores` | `actions_scored.parquet`, `player_leaderboard.parquet` |
| Validation | `skm-validate` | `data/reports/` (generated locally) |
| Dashboard | `streamlit run app/streamlit_app.py` | Interactive explorer |

---

## Quickstart

```bash
git clone https://github.com/ChinmayA301/skm-football.git
cd skm-football
chmod +x scripts/setup_venv.sh
./scripts/setup_venv.sh
source .venv/bin/activate

skm-build-events --max-matches 3
skm-build-scores --max-games 5
skm-validate
streamlit run app/streamlit_app.py
```

Full open-data sample (34 matches):

```bash
skm-build-events
./scripts/run_full_phase2.sh
skm-validate && skm-export-reports
```

---

## v1 limitations

SKM v1 (**SKM-Chance**) is an **action-level** proxy, not the final moment-based metric.

| Finding (Bundesliga 23/24 open sample) | Implication |
|--------------------------------------|-------------|
| ρ(skm, ΔP) ≈ 0.996 | SKM tracks VAEP net value closely today |
| ρ(skm, progressive_per90) ≈ −0.11 | Progressive midfield work is under-rewarded |
| ρ(skm, xG) ≈ 0.25; assists ≈ 0.47 | Not a pure goals/assists stat, but offense-skewed |
| 34-match sample | Not a full season; compare external ratings with care |

Example: **Tella / Boniface** rank high on SKM per90 with modest FotMob season ratings; **Xhaka** has a top FotMob rating but lower v1 SKM—motivation for moment-based v2. Details in [case studies](docs/CASE_STUDIES.md) and [market positioning](docs/SKM_MARKET_POSITIONING.md).

---

## Validation

```bash
skm-export-reports
skm-validate
```

- **Tier 1:** SKM vs ΔP, xT  
- **Tier 2:** vs goals, assists, xG, progressive actions  
- **Tier 3:** vs FotMob benchmarks in [`data/external/bundesliga_2324_benchmarks.csv`](data/external/bundesliga_2324_benchmarks.csv)

Reports are written to `data/reports/` (not committed; regenerate after building scores).

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/ROADMAP.md](docs/ROADMAP.md) | Vision and planned phases (moments → unified SKM) |
| [docs/SKM_MARKET_POSITIONING.md](docs/SKM_MARKET_POSITIONING.md) | What SKM can and cannot claim vs market stats |
| [docs/CASE_STUDIES.md](docs/CASE_STUDIES.md) | Example players (validation narratives) |
| [docs/RELATED_WORK.md](docs/RELATED_WORK.md) | VAEP, xT, and related frameworks |
| [PROGRESS.md](PROGRESS.md) | Implementation status |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Setup, tests, and contribution guide |

---

## Requirements

- Python 3.9+
- `numpy>=1.26,<2.0` (required by socceraction)
- VAEP uses sklearn `GradientBoostingClassifier` by default (no XGBoost/OpenMP required)

See [CONTRIBUTING.md](CONTRIBUTING.md) for install troubleshooting.

---

## Data attribution

This project uses [StatsBomb open data](https://github.com/statsbomb/open-data). Credit StatsBomb in any publication or derivative work.

## License

MIT — see [LICENSE](LICENSE).
