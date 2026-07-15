"""Build a slim data bundle for Streamlit Cloud deployment.

The full actions parquet (~53 MB) is too heavy to commit; the dashboard
only needs a subset of columns. This script writes size-optimized copies
of every parquet the app reads into data/app/ (committed to the repo).
`skm.viz.loaders` falls back to data/app/ when data/processed/ is absent —
which is exactly the situation on Streamlit Cloud.

Run after any pipeline rebuild:  python scripts/make_app_bundle.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skm.config import DATA_PROCESSED, PROJECT_ROOT  # noqa: E402

APP_DATA = PROJECT_ROOT / "data" / "app"

# Columns the dashboard actually consumes (viz modules + tabs)
ACTIONS_COLS = [
    "game_id",
    "period_id",
    "time_seconds",
    "team_id",
    "player_id",
    "type_id",
    "result_id",
    "bodypart_id",
    "delta_p",
    "D",
    "C",
    "R",
    "skm",
    "adjusted_skm",
    "xt_value",
    "position_group",
]

COPY_AS_IS = [
    "player_leaderboard.parquet",
    "player_skm_v2.parquet",
    "player_skm_v3.parquet",
    "player_names.parquet",
    "moments.parquet",
    "moment_players.parquet",
    "games.parquet",
    "events.parquet",
]


def _downcast(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        if df[col].dtype == np.float64:
            df[col] = df[col].astype(np.float32)
    return df


def main() -> int:
    APP_DATA.mkdir(parents=True, exist_ok=True)

    actions = pd.read_parquet(DATA_PROCESSED / "actions_scored.parquet")
    slim = _downcast(actions[[c for c in ACTIONS_COLS if c in actions.columns]].copy())
    slim.to_parquet(APP_DATA / "actions_scored.parquet", index=False)

    for name in COPY_AS_IS:
        src = DATA_PROCESSED / name
        if src.exists():
            _downcast(pd.read_parquet(src)).to_parquet(APP_DATA / name, index=False)

    total = sum(f.stat().st_size for f in APP_DATA.glob("*.parquet")) / 1e6
    for f in sorted(APP_DATA.glob("*.parquet")):
        print(f"{f.name:32s} {f.stat().st_size/1e6:6.1f} MB")
    print(f"{'TOTAL':32s} {total:6.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
