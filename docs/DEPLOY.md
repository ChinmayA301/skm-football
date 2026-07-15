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

## Known limits on Cloud

- The **Label moments** tab appends to `data/external/expert_moment_labels.csv`
  on the app container's ephemeral disk — labels collected on Cloud are
  lost on redeploy. Label locally (or download the CSV via the tab) for
  anything you intend to train on.
- The bundle carries only the columns the dashboard uses; rerunning
  models on Cloud is not supported (and not needed).
- StatsBomb open data attribution applies to the deployed app; the README
  credit covers it.
