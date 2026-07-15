"""Phase 5: segment matches into moments and allocate player involvement.

A *moment* is a short episode of play — a possession phase, a transition, or
a set-piece sequence. The unit of account moves from single actions to
`moment_id`, per the roadmap.

Segmentation rules (disclosed heuristics, not tracked possessions):

- A new moment starts on: period change, possession change (team change),
  a time gap above MOMENT_GAP_S, or a dead-ball restart action.
- Moments are capped at MOMENT_MAX_ACTIONS actions; the continuation is a
  new moment with start_reason="cap".
- moment_type: "set_piece" when the moment starts at a dead-ball action;
  "transition" when it starts at an open-play regain (team change) and the
  first TRANSITION_WINDOW_ACTIONS actions net at least TRANSITION_PROGRESS_M
  meters toward the opponent goal; otherwise "open_play".

Attack direction is inferred per game from shot end locations (home team in
socceraction SPADL attacks left→right), so no network fetch is needed.

Outputs:

- moments.parquet — one row per moment: boundaries, start context, aggregates.
- moment_players.parquet — one row per (moment, player): involvement shares.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

from skm.config import (
    ACTIONS_SCORED_PARQUET,
    MOMENT_GAP_S,
    MOMENT_MAX_ACTIONS,
    MOMENT_PLAYERS_PARQUET,
    MOMENTS_PARQUET,
    TRANSITION_PROGRESS_M,
    TRANSITION_WINDOW_ACTIONS,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEAD_BALL_TYPES = {
    "throw_in",
    "freekick_crossed",
    "freekick_short",
    "corner_crossed",
    "corner_short",
    "goalkick",
    "shot_penalty",
    "shot_freekick",
}
SHOT_TYPES = {"shot", "shot_penalty", "shot_freekick"}

SORT_COLS = ["game_id", "period_id", "time_seconds", "action_id"]


def _named_sorted(actions: pd.DataFrame) -> pd.DataFrame:
    """Return actions with SPADL names, sorted in match order."""
    import socceraction.spadl as spadl

    named = spadl.add_names(actions)
    sort_cols = [c for c in SORT_COLS if c in named.columns]
    return named.sort_values(sort_cols, kind="stable")


def infer_home_teams(actions: pd.DataFrame) -> Dict[int, int]:
    """
    Infer the home team per game from shot end locations.

    socceraction SPADL orients the home team left→right, so the team whose
    shots end at higher x attacks right and is the home team. Falls back to
    the first team observed in the game (with a warning) when a game has no
    usable shots.
    """
    named = _named_sorted(actions)
    home: Dict[int, int] = {}
    for game_id, grp in named.groupby("game_id"):
        shots = grp[grp["type_name"].isin(SHOT_TYPES)].dropna(subset=["end_x"])
        teams = grp["team_id"].unique()
        if len(teams) < 2 or shots["team_id"].nunique() < 1:
            home[int(game_id)] = int(teams[0])
            logger.warning("Game %s: no shots to infer home team; using first team", game_id)
            continue
        mean_x = shots.groupby("team_id")["end_x"].mean()
        home[int(game_id)] = int(mean_x.idxmax())
    return home


def segment_moments(actions: pd.DataFrame) -> pd.DataFrame:
    """
    Assign moment_id and start_reason to each action.

    Returns the named, match-ordered actions with `moment_id` (int) and
    `start_reason` (only set on the first action of each moment).
    """
    df = _named_sorted(actions).copy()

    game_change = df["game_id"] != df["game_id"].shift()
    period_change = (df["period_id"] != df["period_id"].shift()) & ~game_change
    team_change = (df["team_id"] != df["team_id"].shift()) & ~game_change & ~period_change
    gap = (
        ((df["time_seconds"] - df["time_seconds"].shift()) > MOMENT_GAP_S)
        & ~game_change
        & ~period_change
    )
    dead_ball = df["type_name"].isin(DEAD_BALL_TYPES)

    new_moment = game_change | period_change | team_change | gap | dead_ball
    prelim = new_moment.cumsum()

    # Length cap: split every MOMENT_MAX_ACTIONS actions within a moment
    within = df.groupby(prelim).cumcount()
    capped = within // MOMENT_MAX_ACTIONS
    df["moment_id"] = pd.factorize(prelim.astype(str) + "_" + capped.astype(str))[0]

    reason = np.select(
        [
            dead_ball,
            game_change,
            period_change,
            team_change,
            gap,
        ],
        ["set_piece", "game_start", "period", "team_change", "gap"],
        default="",
    )
    # cap-splits start with no other boundary flag
    is_first = df["moment_id"] != df["moment_id"].shift()
    reason = np.where(is_first & (reason == ""), "cap", reason)
    reason = np.where(is_first, reason, "")
    df["start_reason"] = reason
    return df


def _forward_progress(grp: pd.DataFrame, sign: float) -> float:
    """Net meters toward the opponent goal over the first window actions."""
    head = grp.head(TRANSITION_WINDOW_ACTIONS)
    dx = (head["end_x"] - head["start_x"]).fillna(0)
    return float(sign * dx.sum())


def build_moments(
    actions: pd.DataFrame,
    home_teams: Optional[Dict[int, int]] = None,
) -> tuple:
    """
    Segment actions into moments and compute per-moment and per-player tables.

    Returns (moments_df, credits_df, segmented_actions).
    """
    if home_teams is None:
        home_teams = infer_home_teams(actions)

    df = segment_moments(actions)

    # Running score per team (goal = successful shot), for score_diff at start
    df["is_goal"] = (
        df["type_name"].isin(SHOT_TYPES) & (df["result_name"] == "success")
    ).astype(int)
    goals_so_far = (
        df.groupby(["game_id", "team_id"])["is_goal"].cumsum() - df["is_goal"]
    )
    total_goals_before = df.groupby("game_id")["is_goal"].cumsum() - df["is_goal"]
    df["team_goals_before"] = goals_so_far
    df["opp_goals_before"] = total_goals_before - goals_so_far
    df["score_diff_start"] = df["team_goals_before"] - df["opp_goals_before"]

    has_adjusted = "adjusted_skm" in df.columns

    rows = []
    for mid, grp in df.groupby("moment_id", sort=True):
        first = grp.iloc[0]
        game_id = int(first["game_id"])
        team_id = int(first["team_id"])
        sign = 1.0 if home_teams.get(game_id) == team_id else -1.0

        reason = first["start_reason"]
        if reason == "set_piece":
            moment_type = "set_piece"
        elif reason == "team_change" and _forward_progress(grp, sign) >= TRANSITION_PROGRESS_M:
            moment_type = "transition"
        else:
            moment_type = "open_play"

        last = grp.iloc[-1]
        row = {
            "moment_id": int(mid),
            "game_id": game_id,
            "period_id": int(first["period_id"]),
            "team_id": team_id,
            "start_time_s": float(first["time_seconds"]),
            "end_time_s": float(last["time_seconds"]),
            "start_minute": (int(first["period_id"]) - 1) * 45
            + float(first["time_seconds"]) / 60.0,
            "start_reason": reason,
            "moment_type": moment_type,
            "score_diff_start": int(first["score_diff_start"]),
            "n_actions": len(grp),
            "delta_p_sum": float(grp["delta_p"].fillna(0).sum()),
            "skm_sum": float(grp["skm"].fillna(0).sum()),
            "contains_shot": bool(grp["type_name"].isin(SHOT_TYPES).any()),
            "contains_goal": bool(grp["is_goal"].any()),
        }
        if has_adjusted:
            row["adjusted_skm_sum"] = float(grp["adjusted_skm"].fillna(0).sum())
        rows.append(row)

    moments = pd.DataFrame(rows)

    # Player involvement per moment
    credits = (
        df[df["player_id"].notna()]
        .groupby(["moment_id", "player_id"])
        .agg(
            n_actions=("moment_id", "size"),
            skm_sum=("skm", "sum"),
            delta_p_sum=("delta_p", "sum"),
        )
        .reset_index()
    )
    moment_sizes = credits.groupby("moment_id")["n_actions"].transform("sum")
    credits["involvement_share"] = credits["n_actions"] / moment_sizes
    credits = credits.merge(
        moments[["moment_id", "game_id", "team_id", "moment_type", "contains_shot"]],
        on="moment_id",
        how="left",
    )

    return moments, credits, df


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Build moments (Phase 5)")
    parser.add_argument("--actions-input", default=str(ACTIONS_SCORED_PARQUET))
    parser.add_argument("--moments-output", default=str(MOMENTS_PARQUET))
    parser.add_argument("--credits-output", default=str(MOMENT_PLAYERS_PARQUET))
    args = parser.parse_args(argv)

    actions = pd.read_parquet(args.actions_input)
    logger.info("Loaded %s scored actions (%s games)", len(actions), actions["game_id"].nunique())

    moments, credits, _ = build_moments(actions)

    for path, frame, label in [
        (Path(args.moments_output), moments, "moments"),
        (Path(args.credits_output), credits, "moment player credits"),
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(path, index=False)
        logger.info("Wrote %s %s → %s", len(frame), label, path)

    print("\nMoment type distribution:")
    print(moments["moment_type"].value_counts().to_string())
    print(f"\nMoments containing a shot: {moments['contains_shot'].mean():.1%}")
    print(f"Median actions per moment: {moments['n_actions'].median():.0f}")

    # Roadmap success criterion: same player, different matches → different portfolios
    per_match = (
        credits.groupby(["player_id", "game_id"])["moment_id"].nunique().groupby("player_id")
    )
    varied = (per_match.std().fillna(0) > 0).mean()
    print(f"Players with varying per-match moment counts: {varied:.1%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
