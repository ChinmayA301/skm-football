"""Phase 2: train components and write scored actions + player leaderboard."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

from skm.config import (
    ACTIONS_SCORED_PARQUET,
    DEFAULT_COMPETITION,
    DEFAULT_SEASON,
    EVENTS_PARQUET,
    PLAYER_LEADERBOARD_PARQUET,
)
from skm.models.context import compute_context
from skm.models.difficulty import compute_difficulty, fit_difficulty_model
from skm.models.role import compute_role, fit_role_clusters
from skm.models.skm_combine import combine_adjusted_skm, combine_skm, player_leaderboard
from skm.models.weights import (
    attach_player_positions,
    compute_game_state_weight,
    compute_position_weight,
    compute_role_weight,
    compute_sequence_weight,
)
from skm.models.booster_compat import stub_broken_boosters
from skm.models.spadl_convert import build_spadl_actions, resolve_competition_ids
from skm.models.vaep_delta import rate_all_actions, train_vaep

stub_broken_boosters()
from skm.models.xthreat_value import fit_and_rate_xt

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _attach_event_pressure(actions: pd.DataFrame) -> pd.DataFrame:
    """Merge under_pressure from StatsBomb events onto SPADL actions."""
    from socceraction.data.statsbomb import StatsBombLoader

    sbl = StatsBombLoader(getter="remote")
    parts = []
    for game_id, grp in actions.groupby("game_id"):
        ev = sbl.events(int(game_id))[["event_id", "under_pressure"]]
        merged = grp.merge(
            ev,
            left_on="original_event_id",
            right_on="event_id",
            how="left",
        )
        merged["under_pressure"] = merged["under_pressure"].fillna(False)
        parts.append(merged.drop(columns=["event_id"], errors="ignore"))
    return pd.concat(parts, ignore_index=True)


def run_phase2(
    competition: str = DEFAULT_COMPETITION,
    season: str = DEFAULT_SEASON,
    max_games: Optional[int] = None,
    skip_xt: bool = False,
    competitions: Optional[list] = None,
) -> pd.DataFrame:
    """competitions: optional list of (competition_name, season_name) pairs;
    overrides the single competition/season arguments when given."""
    pairs = competitions or [(competition, season)]

    action_parts, game_parts = [], []
    for comp_name, season_name in pairs:
        cid, sid = resolve_competition_ids(comp_name, season_name)
        logger.info("Phase 2: %s %s (competition_id=%s)", comp_name, season_name, cid)
        part_actions, part_games = build_spadl_actions(cid, sid, max_games=max_games)
        part_games = part_games.copy()
        part_games["competition"] = comp_name
        part_games["season"] = season_name
        action_parts.append(part_actions)
        game_parts.append(part_games)

    actions = pd.concat(action_parts, ignore_index=True)
    games = pd.concat(game_parts)
    logger.info("SPADL actions: %s rows across %s games", len(actions), actions["game_id"].nunique())

    actions = _attach_event_pressure(actions)

    vaep = train_vaep(games, actions)
    actions = rate_all_actions(games, actions, vaep)

    d_model, d_scaler, d_cols = fit_difficulty_model(actions)
    actions["D"] = compute_difficulty(actions, d_model, d_scaler, d_cols).values

    actions["C"] = compute_context(actions, games).values

    role_state = fit_role_clusters(actions)
    actions["R"] = compute_role(actions, role_state).values

    if not skip_xt:
        try:
            actions["xt_value"] = fit_and_rate_xt(actions, games).values
        except Exception as exc:
            logger.warning("xT failed (%s); setting xt_value=0", exc)
            actions["xt_value"] = 0.0
    else:
        actions["xt_value"] = 0.0

    actions["skm"] = combine_skm(actions).values

    # v1.5 weighting layer → adjusted_skm
    try:
        actions = attach_player_positions(actions)
    except Exception as exc:
        logger.warning("Position fetch failed (%s); position_weight=1.0", exc)
        actions["position_group"] = None
    actions["position_weight"] = compute_position_weight(actions).values
    actions["role_weight"] = compute_role_weight(actions, role_state).values
    actions["game_state_weight"] = compute_game_state_weight(actions, games).values
    actions["sequence_weight"] = compute_sequence_weight(actions).values
    actions["adjusted_skm"] = combine_adjusted_skm(actions).values

    return actions, games


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Build SKM scores (Phase 2)")
    parser.add_argument("--competition", default=DEFAULT_COMPETITION)
    parser.add_argument("--season", default=DEFAULT_SEASON)
    parser.add_argument(
        "--competitions",
        default=None,
        help='Multiple competitions as "Name:Season,Name:Season" (overrides --competition/--season)',
    )
    parser.add_argument("--max-games", type=int, default=None)
    parser.add_argument("--actions-output", default=str(ACTIONS_SCORED_PARQUET))
    parser.add_argument("--leaderboard-output", default=str(PLAYER_LEADERBOARD_PARQUET))
    parser.add_argument("--skip-xt", action="store_true")
    args = parser.parse_args(argv)

    competitions = None
    if args.competitions:
        competitions = [
            tuple(pair.split(":", 1)) for pair in args.competitions.split(",") if ":" in pair
        ]

    actions, games = run_phase2(
        competition=args.competition,
        season=args.season,
        max_games=args.max_games,
        skip_xt=args.skip_xt,
        competitions=competitions,
    )

    actions_path = Path(args.actions_output)
    actions_path.parent.mkdir(parents=True, exist_ok=True)
    actions.to_parquet(actions_path, index=False)
    logger.info("Wrote actions → %s", actions_path)

    from skm.config import GAMES_PARQUET

    games.reset_index().to_parquet(GAMES_PARQUET, index=False)
    logger.info("Wrote games metadata → %s", GAMES_PARQUET)

    board = player_leaderboard(actions, games)
    board_path = Path(args.leaderboard_output)
    board.to_parquet(board_path, index=False)
    logger.info("Wrote leaderboard (%s players) → %s", len(board), board_path)

    if EVENTS_PARQUET.exists():
        logger.info(
            "Events parquet at %s (join via game_id=match_id + original_event_id)",
            EVENTS_PARQUET,
        )

    print("\nTop 10 by SKM per 90 (estimated minutes):")
    print(board.head(10).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
