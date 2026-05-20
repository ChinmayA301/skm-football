"""Load processed datasets for visualization."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

from skm.config import (
    ACTIONS_SCORED_PARQUET,
    EVENTS_PARQUET,
    PLAYER_LEADERBOARD_PARQUET,
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


def load_leaderboard() -> pd.DataFrame:
    if PLAYER_LEADERBOARD_PARQUET.exists():
        return pd.read_parquet(PLAYER_LEADERBOARD_PARQUET)
    actions = load_actions()
    from skm.models.skm_combine import player_leaderboard

    return player_leaderboard(actions, games=pd.DataFrame())


def player_name_map(events: Optional[pd.DataFrame] = None) -> pd.Series:
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
