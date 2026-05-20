"""Match-level cumulative SKM timelines."""

from __future__ import annotations

from typing import Optional, Tuple

import pandas as pd

from skm.viz.loaders import load_actions


def _minute_from_action(row: pd.Series) -> float:
    return (max(int(row.get("period_id", 1)), 1) - 1) * 45 + float(row.get("time_seconds", 0)) / 60.0


def match_timeline_data(
    game_id: int,
    actions: Optional[pd.DataFrame] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Return (team_cumulative, goals) for plotting.

    team_cumulative columns: minute, team_id, skm_cum
    goals columns: minute, team_id, label
    """
    if actions is None:
        actions = load_actions()

    df = actions[actions["game_id"] == int(game_id)].copy()
    if df.empty:
        raise ValueError(f"No actions for game_id={game_id}")

    df["minute"] = df.apply(_minute_from_action, axis=1)
    df = df.sort_values(["minute", "time_seconds"])

    team_cum = (
        df.groupby(["team_id", "minute"], as_index=False)["skm"]
        .sum()
        .sort_values(["team_id", "minute"])
    )
    team_cum["skm_cum"] = team_cum.groupby("team_id")["skm"].cumsum()

    goals = pd.DataFrame(columns=["minute", "team_id", "label"])
    if "type_id" in df.columns:
        import socceraction.spadl as spadl

        named = spadl.add_names(df)
        shot_goals = named[
            named["type_name"].str.contains("shot", na=False)
            & (named["result_name"] == "success")
        ].copy()
        if not shot_goals.empty:
            goals = shot_goals[["minute", "team_id"]].copy()
            goals["label"] = "Goal"

    return team_cum, goals


def list_match_ids(actions: Optional[pd.DataFrame] = None) -> list:
    if actions is None:
        actions = load_actions()
    return sorted(actions["game_id"].unique().astype(int).tolist())
