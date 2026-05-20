"""Per-player SKM component breakdown for radar charts."""

from __future__ import annotations

from typing import Optional

import pandas as pd

from skm.viz.loaders import load_actions, player_name_map


def player_component_summary(
    player_id: int,
    actions: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Mean D, C, R and sum delta_p / skm for one player."""
    if actions is None:
        actions = load_actions()

    sub = actions[actions["player_id"] == int(player_id)]
    if sub.empty:
        raise ValueError(f"No actions for player_id={player_id}")

    return pd.DataFrame(
        [
            {
                "player_id": player_id,
                "n_actions": len(sub),
                "delta_p_sum": sub["delta_p"].sum(),
                "skm_sum": sub["skm"].sum(),
                "D_mean": sub["D"].mean(),
                "C_mean": sub["C"].mean(),
                "R_mean": sub["R"].mean(),
                "xt_sum": sub.get("xt_value", pd.Series([0])).sum(),
            }
        ]
    )


def list_players(actions: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    if actions is None:
        actions = load_actions()
    names = player_name_map()
    counts = actions.groupby("player_id")["skm"].agg(["sum", "count"]).reset_index()
    counts.columns = ["player_id", "skm_total", "n_actions"]
    counts["player"] = counts["player_id"].map(names)
    return counts.sort_values("skm_total", ascending=False)
