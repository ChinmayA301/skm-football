"""Convert StatsBomb matches to SPADL actions via socceraction."""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


def _loader():
    from socceraction.data.statsbomb import StatsBombLoader

    return StatsBombLoader(getter="remote")


def resolve_competition_ids(
    competition_name: str,
    season_name: str,
) -> Tuple[int, int]:
    from skm.data.download import resolve_competition_season

    cid, sid, _ = resolve_competition_season(competition_name, season_name)
    return cid, sid


def load_games(competition_id: int, season_id: int) -> pd.DataFrame:
    sbl = _loader()
    games = sbl.games(competition_id, season_id)
    return games.set_index("game_id")


def convert_match_to_spadl(game_id: int, games: pd.DataFrame) -> pd.DataFrame:
    import socceraction.spadl.statsbomb as spadl_statsbomb

    sbl = _loader()
    events = sbl.events(int(game_id))
    home_team_id = int(games.loc[game_id, "home_team_id"])
    actions = spadl_statsbomb.convert_to_actions(events, home_team_id)
    actions["game_id"] = int(game_id)
    return actions


def build_spadl_actions(
    competition_id: int,
    season_id: int,
    max_games: Optional[int] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Return (actions, games_indexed_by_game_id)."""
    games = load_games(competition_id, season_id)
    game_ids = list(games.index.astype(int))
    if max_games is not None:
        game_ids = game_ids[:max_games]

    frames: List[pd.DataFrame] = []
    for gid in game_ids:
        try:
            frames.append(convert_match_to_spadl(gid, games))
        except Exception as exc:
            logger.warning("SPADL conversion failed for game %s: %s", gid, exc)

    if not frames:
        raise RuntimeError("No SPADL actions produced.")

    actions = pd.concat(frames, ignore_index=True)
    return actions, games
