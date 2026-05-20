"""Players who rank high on SKM but low on traditional outputs."""

from __future__ import annotations

from typing import Optional

import pandas as pd

from skm.viz.loaders import enrich_leaderboard, load_events, load_leaderboard


def _goals_per90_from_actions(actions: pd.DataFrame) -> pd.DataFrame:
    """Goals per 90 from successful shots in SPADL actions."""
    import socceraction.spadl as spadl

    named = spadl.add_names(actions)
    goals = named[
        named["type_name"].str.contains("shot", na=False)
        & (named["result_name"] == "success")
    ]
    if goals.empty:
        return pd.DataFrame(columns=["player_id", "goals_per90"])

    gcount = goals.groupby("player_id").size().reset_index(name="goals")
    mins = (
        actions.dropna(subset=["player_id"])
        .groupby("player_id")
        .size()
        .reset_index(name="n_actions")
    )
    merged = gcount.merge(mins, on="player_id")
    rate = merged["n_actions"].median() / 90.0 if len(merged) else 1.0
    merged["minutes_est"] = merged["n_actions"] / max(rate, 1e-6)
    merged["goals_per90"] = merged["goals"] / merged["minutes_est"] * 90.0
    return merged[["player_id", "goals_per90"]]


def hidden_heroes_table(
    board: Optional[pd.DataFrame] = None,
    actions: Optional[pd.DataFrame] = None,
    events: Optional[pd.DataFrame] = None,
    top_n: int = 25,
) -> pd.DataFrame:
    """
    Rank gap: SKM per 90 vs xT per 90 (and goals per 90 when available).

    Large positive skm_minus_xt_rank → SKM values player more than xT.
    """
    from skm.viz.loaders import load_actions

    if board is None:
        board = enrich_leaderboard(load_leaderboard())
    if actions is None:
        actions = load_actions()
    if events is None:
        events = load_events()

    df = board.copy()
    goals = _goals_per90_from_actions(actions)
    df = df.merge(goals, on="player_id", how="left")
    df["goals_per90"] = df["goals_per90"].fillna(0)

    for col in ("skm_per90", "delta_p_per90", "xt_per90", "goals_per90"):
        df[f"{col}_rank"] = df[col].rank(ascending=False, method="min")

    df["skm_minus_xt_rank"] = df["xt_per90_rank"] - df["skm_per90_rank"]
    df["skm_minus_goals_rank"] = df["goals_per90_rank"] - df["skm_per90_rank"]

    cols = [
        "player",
        "player_id",
        "skm_per90",
        "delta_p_per90",
        "xt_per90",
        "goals_per90",
        "skm_minus_xt_rank",
        "skm_minus_goals_rank",
        "n_actions",
    ]
    cols = [c for c in cols if c in df.columns]
    return df.sort_values("skm_minus_xt_rank", ascending=False).head(top_n)[cols]


def role_fairness_by_type(actions: pd.DataFrame) -> pd.DataFrame:
    """Mean SKM by SPADL action type — check attacker bias."""
    import socceraction.spadl as spadl

    named = spadl.add_names(actions)
    return (
        named.groupby("type_name")["skm"]
        .agg(["mean", "count"])
        .sort_values("mean", ascending=False)
        .reset_index()
    )
