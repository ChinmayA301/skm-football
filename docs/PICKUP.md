# Resume SKM — start here

**Project:** `~/Documents/projects/skm`  
**Version:** v0.1.0 (SKM-Chance, action-level)  
**Plans:** [BUILD_PLAN.md](BUILD_PLAN.md) (v1 publish) · [COMPLETE_BUILD_PLAN.md](COMPLETE_BUILD_PLAN.md) (full Phases 1–8)

---

## 1. Environment

```bash
cd ~/Documents/projects/skm
source .venv/bin/activate
```

If broken: `./scripts/setup_venv.sh` or README “setup failed on scipy” block.

---

## 2. Confirm data exists

```bash
ls -lh data/processed/events.parquet data/processed/player_leaderboard.parquet
```

Missing? Run Phase 1 then Phase 2:

```bash
skm-build-events
./scripts/run_full_phase2.sh
```

---

## 3. Dashboard + validation

```bash
streamlit run app/streamlit_app.py
skm-validate && skm-export-reports
```

Reports → `data/reports/` (local only).

---

## 4. Still to do (v1 publish)

- [ ] `pytest && ruff check src tests` (in your Terminal)
- [ ] `./scripts/publish_to_github.sh skm-football YOUR_GITHUB_USERNAME`
- [ ] Push to public `skm-football`
- [ ] Optional: blog using `docs/CASE_STUDIES.md` + report charts

---

## 5. Next build (v2)

Read [ROADMAP.md](ROADMAP.md) Phase 5 → implement `src/skm/models/moments.py` first.

**Design lock:** Final product = single `skm_per90` after Phase 6; parallel metrics only for internal calibration until then.
