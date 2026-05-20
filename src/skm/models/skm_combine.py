"""Combine ΔP, D, C, R into final SKM score."""

from __future__ import annotations

import pandas as pd

from skm.config import SKM_W_C, SKM_W_D, SKM_W_R


def combine_skm(
    actions: pd.DataFrame,
    delta_p_col: str = "delta_p",
    d_col: str = "D",
    c_col: str = "C",
    r_col: str = "R",
) -> pd.Series:
    """
    SKM_i = ΔP_i × (1 + w_d·D_i + w_c·C_i + w_r·R_i)

    D, C, R are multipliers centered around 1.0 in their construction.
    """
    dp = actions[delta_p_col].fillna(0)
    d = actions[d_col].fillna(1.0)
    c = actions[c_col].fillna(1.0)
    r = actions[r_col].fillna(1.0)
    return dp * (1.0 + SKM_W_D * d + SKM_W_C * c + SKM_W_R * r)


def player_leaderboard(
    actions: pd.DataFrame,
    games: pd.DataFrame,
    min_actions: int = 400,
) -> pd.DataFrame:
    """Per-player SKM and ΔP per 90 (minutes estimated from action counts)."""
    agg = (
        actions.groupby("player_id")
        .agg(
            skm_total=("skm", "sum"),
            delta_p_total=("delta_p", "sum"),
            xt_total=("xt_value", "sum"),
            n_actions=("skm", "count"),
        )
        .reset_index()
    )

    agg = agg[agg["n_actions"] >= min_actions]
    actions_per_minute = agg["n_actions"].sum() / max(len(actions) / 90.0, 1.0)
    agg["minutes_est"] = agg["n_actions"] / max(actions_per_minute / 90.0, 1e-6)

    agg["skm_per90"] = agg["skm_total"] / agg["minutes_est"] * 90.0
    agg["delta_p_per90"] = agg["delta_p_total"] / agg["minutes_est"] * 90.0
    agg["xt_per90"] = agg["xt_total"] / agg["minutes_est"] * 90.0

    return agg.sort_values("skm_per90", ascending=False)
