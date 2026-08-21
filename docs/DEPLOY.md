# Deploying the dashboard to Streamlit Cloud

The app reads from `data/processed/` when present (local dev) and falls
back to the slim committed bundle in `data/app/` (~31 MB, built by
`scripts/make_app_bundle.py`). Streamlit Cloud clones the repo, installs
`requirements.txt`, and runs the app against the bundle — no pipeline run
needed at boot.

## One-time setup

1. Push the branch with `data/app/` committed.
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app.
3. Repository: `ChinmayA301/skm-football` · Branch: your deploy branch ·
   Main file path: `app/streamlit_app.py`.
4. Python version: 3.9–3.11 (Advanced settings). No secrets required —
   everything runs on committed open data.

## Refreshing the deployed data

After any pipeline rebuild:

```bash
python scripts/make_app_bundle.py
git add data/app && git commit -m "Refresh app data bundle" && git push
```

Streamlit Cloud redeploys on push.

## Why `requirements.txt` is dashboard-only

The deployed app only *reads* the committed bundle — it never trains models.
So `requirements.txt` deliberately excludes `socceraction`, `scikit-learn`
and `statsbombpy`:

- `socceraction` pins `numpy<2`, which caps the deployable Python at 3.12.
  Streamlit Cloud builds on newer Pythons (3.14 at time of writing), where
  no `numpy<2` / `pandas 2.2` wheels exist — pip then tries to compile pandas
  from source and the build fails.
- The only thing the dashboard needed socceraction for was SPADL
  `type_name` / `result_name` labels. Those are now **baked into the bundle**
  by `scripts/make_app_bundle.py` and read via `skm.viz.naming`.

So: after regenerating data, always rerun `python scripts/make_app_bundle.py`
(it bakes the labels), and keep the deploy requirements ranges loose so pip
can pick wheels for whatever Python the platform runs.

The app also adds `src/` to `sys.path` at startup, since Streamlit Cloud runs
the repo in place without `pip install -e .`.

## Known limits on Cloud

- The **Label moments** tab appends to `data/external/expert_moment_labels.csv`
  on the app container's ephemeral disk — labels collected on Cloud are
  lost on redeploy. Label locally (or download the CSV via the tab) for
  anything you intend to train on.
- The bundle carries only the columns the dashboard uses; rerunning
  models on Cloud is not supported (and not needed).
- StatsBomb open data attribution applies to the deployed app; the README
  credit covers it.
