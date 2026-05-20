# SKM Build Progress

**v1 = SKM-Chance** (action-level proxy). **v2 = unified `skm_per90`** from moment credits ([Phase 6](docs/ROADMAP.md)).

**Resume:** [docs/PICKUP.md](docs/PICKUP.md) · **v1 publish plan:** [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md) · **Master plan (Phases 1–8):** [docs/COMPLETE_BUILD_PLAN.md](docs/COMPLETE_BUILD_PLAN.md)

## Phase 1: Data foundation
- [x] Project scaffold (`pyproject.toml`, `src/skm`, README)
- [x] StatsBomb ingest pipeline
- [x] Event feature engineering (zone, progressive, scoreline, minute bucket)
- [x] Full extract → `data/processed/events.parquet` (1. Bundesliga 2023/24, 34 matches, 137,765 events)
- [x] Optional columns for validation: `shot_xg`, `pass_goal_assist` (re-run `skm-build-events` to refresh)

## Phase 2: Component models
- [x] ΔP via sklearn VAEP fallback (`vaep_sklearn.py`, `vaep_delta.py`)
- [x] Difficulty (D), Context (C), Role (R), xT, SKM combine
- [x] Smoke test: `skm-build-scores --max-games 5` succeeded
- [ ] **Full run:** `./scripts/run_full_phase2.sh` (all 34 matches — confirm in Terminal)

## Phase 3: Validation & viz
- [x] Streamlit app + **Validation** tab
- [x] `skm-validate` / `scripts/validation_benchmarks.py`
- [x] `skm-export-reports` (includes validation scatter + CSV)
- [x] `notebooks/03_validation_benchmarks.ipynb`
- [x] `data/external/bundesliga_2324_benchmarks.csv` (FotMob BL 23/24)
- [x] `docs/CASE_STUDIES.md` (illustrative player buckets)
- [x] `docs/RELATED_WORK.md`

## Phase 4: Publish (GitHub v1)
- [x] `docs/ROADMAP.md` (Phases 5–8)
- [x] `docs/SKM_MARKET_POSITIONING.md`
- [x] `docs/BUILD_PLAN.md` + `docs/COMPLETE_BUILD_PLAN.md` + `docs/PICKUP.md` (local plans for future sessions)
- [x] README landing page + doc index
- [x] Illustrative case studies (Tella, Boniface, Wirtz, Grimaldo, Xhaka, Kane)
- [ ] Run `scripts/publish_to_github.sh skm-football YOUR_USERNAME` + `git push`
- [ ] Blog post with charts from local `data/reports/`
- [ ] Optional: Streamlit Community Cloud

## Notes
- v1 formula: `SKM_i = ΔP_i × (1 + w_d·D_i + w_c·C_i + w_r·R_i)`, weights 0.3
- VAEP: sklearn GBM (no libomp / Homebrew required)
- Validation: Tier 1 internal → Tier 2 outcomes → Tier 3 public CSV → Tier 4 narratives
