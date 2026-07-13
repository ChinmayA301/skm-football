"""Load processed datasets for visualization."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

from skm.config import (
    ACTIONS_SCORED_PARQUET,
    EVENTS_PARQUET,
    MOMENT_PLAYERS_PARQUET,
    MOMENTS_PARQUET,
    PLAYER_LEADERBOARD_PARQUET,
    PLAYER_SKM_V2_PARQUET,
    PROJECT_ROOT,
)

# Slim committed bundle (scripts/make_app_bundle.py) — used on Streamlit
# Cloud where data/processed/ is not built.
APP_DATA = PROJECT_ROOT / "data" / "app"


class DataNotFoundError(FileNotFoundError):
    pass


def require_file(path: Path, hint: str) -> Path:
    if path.exists():
        return path
    bundled = APP_DATA / path.name
    if bundled.exists():
        return bundled
    raise DataNotFoundError(f"Missing {path.name}. {hint}")


def load_actions() -> pd.DataFrame:
    return pd.read_parquet(require_file(ACTIONS_SCORED_PARQUET, "Run: skm-build-scores"))


def load_events() -> pd.DataFrame:
    return pd.read_parquet(require_file(EVENTS_PARQUET, "Run: skm-build-events"))


def load_moments() -> pd.DataFrame:
    return pd.read_parquet(require_file(MOMENTS_PARQUET, "Run: skm-build-moments"))


def load_moment_players() -> pd.DataFrame:
    return pd.read_parquet(require_file(MOMENT_PLAYERS_PARQUET, "Run: skm-build-moments"))


def load_v2_board() -> pd.DataFrame:
    return pd.read_parquet(require_file(PLAYER_SKM_V2_PARQUET, "Run: skm-build-credits"))


def load_leaderboard() -> pd.DataFrame:
    for path in (PLAYER_LEADERBOARD_PARQUET, APP_DATA / PLAYER_LEADERBOARD_PARQUET.name):
        if path.exists():
            return pd.read_parquet(path)
    actions = load_actions()
    from skm.models.skm_combine import player_leaderboard

    return player_leaderboard(actions, games=pd.DataFrame())


def player_name_map(events: Optional[pd.DataFrame] = None) -> pd.Series:
    """player_id → name. Prefers the lineup-based names parquet (covers all
    competitions); falls back to events.parquet (original sample only)."""
    for names_path in (
        ACTIONS_SCORED_PARQUET.parent / "player_names.parquet",
        APP_DATA / "player_names.parquet",
    ):
        if names_path.exists():
            names = pd.read_parquet(names_path)
            return names.set_index("player_id")["player_name"]
    if events is None:
        events = load_events()
    return events.dropna(subset=["player_id"]).groupby("player_id")["player"].first()


def enrich_leaderboard(
    board: pd.DataFrame,
    events: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    names = player_name_map(events)
    out = board.copy()
    out["player"] = out["player_id"].map(names)
    return out


def load_all() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    actions = load_actions()
    events = load_events()
    board = enrich_leaderboard(load_leaderboard(), events)
    return actions, events, board
