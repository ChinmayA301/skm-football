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
)


class DataNotFoundError(FileNotFoundError):
    pass


def require_file(path: Path, hint: str) -> Path:
    if not path.exists():
        raise DataNotFoundError(f"Missing {path.name}. {hint}")
    return path


def load_actions() -> pd.DataFrame:
    require_file(ACTIONS_SCORED_PARQUET, "Run: skm-build-scores")
    return pd.read_parquet(ACTIONS_SCORED_PARQUET)


def load_events() -> pd.DataFrame:
    require_file(EVENTS_PARQUET, "Run: skm-build-events")
    return pd.read_parquet(EVENTS_PARQUET)


def load_moments() -> pd.DataFrame:
    require_file(MOMENTS_PARQUET, "Run: skm-build-moments")
    return pd.read_parquet(MOMENTS_PARQUET)


def load_moment_players() -> pd.DataFrame:
    require_file(MOMENT_PLAYERS_PARQUET, "Run: skm-build-moments")
    return pd.read_parquet(MOMENT_PLAYERS_PARQUET)


def load_v2_board() -> pd.DataFrame:
    require_file(PLAYER_SKM_V2_PARQUET, "Run: skm-build-credits")
    return pd.read_parquet(PLAYER_SKM_V2_PARQUET)


def load_leaderboard() -> pd.DataFrame:
    if PLAYER_LEADERBOARD_PARQUET.exists():
        return pd.read_parquet(PLAYER_LEADERBOARD_PARQUET)
    actions = load_actions()
    from skm.models.skm_combine import player_leaderboard

    return player_leaderboard(actions, games=pd.DataFrame())


def player_name_map(events: Optional[pd.DataFrame] = None) -> pd.Series:
    """player_id → name. Prefers the lineup-based names parquet (covers all
    competitions); falls back to events.parquet (original sample only)."""
    names_path = ACTIONS_SCORED_PARQUET.parent / "player_names.parquet"
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
