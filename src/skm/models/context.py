"""Context multiplier C from minute, scoreline, and opponent quality."""

from __future__ import annotations

import numpy as np
import pandas as pd

from skm.config import C_CLIP


def attach_game_context(actions: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    """Add home_team_id, approximate minute, and running score per action."""
    out = actions.copy()
    out = out.merge(
        games[["home_team_id", "away_team_id"]],
        left_on="game_id",
        right_index=True,
        how="left",
    )
    out["minute_approx"] = (out["period_id"].clip(lower=1) - 1) * 45 + out["time_seconds"] / 60.0

    import socceraction.spadl as spadl

    named = spadl.add_names(out)
    out["is_goal"] = (
        named["type_name"].str.contains("shot", na=False)
        & (named["result_name"] == "success")
    ).astype(int)

    out["home_score_live"] = 0
    out["away_score_live"] = 0

    for game_id, grp in out.groupby("game_id"):
        grp = grp.sort_values(["period_id", "time_seconds"])
        home_id = int(grp["home_team_id"].iloc[0])
        hs, as_ = 0, 0
        h_list, a_list = [], []
        for _, row in grp.iterrows():
            if row["is_goal"]:
                if int(row["team_id"]) == home_id:
                    hs += 1
                else:
                    as_ += 1
            h_list.append(hs)
            a_list.append(as_)
        out.loc[grp.index, "home_score_live"] = h_list
        out.loc[grp.index, "away_score_live"] = a_list

    out["team_is_home"] = out["team_id"] == out["home_team_id"]
    out["team_score_live"] = np.where(
        out["team_is_home"], out["home_score_live"], out["away_score_live"]
    )
    out["opp_score_live"] = np.where(
        out["team_is_home"], out["away_score_live"], out["home_score_live"]
    )
    out["score_diff"] = out["team_score_live"] - out["opp_score_live"]
    return out


def compute_context(actions: pd.DataFrame, games: pd.DataFrame) -> pd.Series:
    """C: higher in late close games and when trailing/drawing."""
    df = attach_game_context(actions, games)

    minute_w = 1.0 + 0.5 * (df["minute_approx"] >= 75).astype(float)
    close_game = df["score_diff"].abs() <= 1
    minute_w = np.where(close_game & (df["minute_approx"] >= 60), minute_w + 0.3, minute_w)

    score_w = np.ones(len(df))
    score_w = np.where(df["score_diff"] == 0, 1.15, score_w)
    score_w = np.where(df["score_diff"] == -1, 1.25, score_w)

    c = minute_w * score_w
    return pd.Series(np.clip(c, C_CLIP[0], C_CLIP[1]), index=actions.index)
