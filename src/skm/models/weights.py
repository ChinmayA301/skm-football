"""Adjusted SKM weighting layer (v1.5).

Adjusted SKM = Base SKM × position_weight × role_weight × game_state_weight × sequence_weight

Design notes / limitations (disclosed, not hidden):

- **position_weight** uses a hand-set prior table mapping position groups to
  SPADL action-type importance. Values are deliberately modest (0.9–1.25) and
  are priors, not fitted parameters.
- **role_weight** is data-driven: how central an action type is to the
  player's role cluster (from `skm.models.role`) relative to the global rate.
  This is the opposite direction of the v1 R factor, which rewards *unusual*
  actions; role_weight rewards actions the role is *responsible* for.
- **game_state_weight** captures leverage extremes (garbage time down,
  late-close up). It intentionally overlaps a little with C, which encodes
  trailing/drawing incentive — both are kept modest to limit double counting.
- **sequence_weight** upweights non-shooting actions in same-team chains that
  end in a shot, so the final actor is not the only one credited.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

import numpy as np
import pandas as pd

from skm.config import (
    GAME_STATE_W_CLIP,
    GAME_STATE_W_GARBAGE,
    GAME_STATE_W_LATE_CLOSE,
    POSITION_W_CLIP,
    ROLE_W_CLIP,
    SEQUENCE_CHAIN_GAP_S,
    SEQUENCE_MIN_CHAIN_LEN,
    SEQUENCE_SHOT_BOOST,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Position weight
# ---------------------------------------------------------------------------

POSITION_GROUPS = ["GK", "CB", "FB", "DM", "CM", "AM", "W", "ST"]

# Prior table: how important each SPADL action type is for a position group.
# Missing (group, type) pairs default to 1.0. Values are conservative priors.
POSITION_ACTION_WEIGHTS: Dict[str, Dict[str, float]] = {
    "GK": {
        "keeper_save": 1.25,
        "keeper_claim": 1.2,
        "keeper_punch": 1.15,
        "keeper_pick_up": 1.1,
        "pass": 1.1,
        "goalkick": 1.1,
        "clearance": 1.1,
    },
    "CB": {
        "clearance": 1.2,
        "interception": 1.15,
        "tackle": 1.15,
        "pass": 1.1,
    },
    "FB": {
        "cross": 1.2,
        "dribble": 1.1,
        "tackle": 1.1,
        "interception": 1.05,
    },
    "DM": {
        "interception": 1.25,
        "tackle": 1.2,
        "foul": 1.1,  # tactical fouls killing transitions
        "pass": 1.1,
    },
    "CM": {
        "pass": 1.15,
        "dribble": 1.1,
        "interception": 1.05,
    },
    "AM": {
        "pass": 1.15,
        "take_on": 1.15,
        "shot": 1.05,
    },
    "W": {
        "take_on": 1.25,
        "cross": 1.2,
        "dribble": 1.15,
        "shot": 1.05,
    },
    "ST": {
        "shot": 1.2,
        "take_on": 1.05,
    },
}


def map_position_group(position_name: object) -> Optional[str]:
    """Map a StatsBomb starting_position_name to a coarse position group."""
    if not isinstance(position_name, str):
        return None
    name = position_name.strip()
    if not name or name == "Substitute":
        return None
    if "Goalkeeper" in name:
        return "GK"
    if "Center Back" in name:
        return "CB"
    if "Back" in name:  # Left/Right Back, Wing Back
        return "FB"
    if "Defensive Midfield" in name:
        return "DM"
    if "Attacking Midfield" in name:
        return "AM" if "Center" in name else "W"
    if "Wing" in name:
        return "W"
    if "Midfield" in name:  # Left/Right/Center Midfield
        return "CM"
    if "Forward" in name or "Striker" in name:
        return "ST"
    return None


def attach_player_positions(actions: pd.DataFrame) -> pd.DataFrame:
    """Merge starting position group per (game_id, player_id) from lineups."""
    from socceraction.data.statsbomb import StatsBombLoader

    sbl = StatsBombLoader(getter="remote")
    frames = []
    for game_id in actions["game_id"].unique():
        try:
            players = sbl.players(int(game_id))
        except Exception as exc:
            logger.warning("Lineup fetch failed for game %s: %s", game_id, exc)
            continue
        players = players[["game_id", "player_id", "starting_position_name"]].copy()
        frames.append(players)

    out = actions.copy()
    if not frames:
        out["position_group"] = None
        return out

    lineups = pd.concat(frames, ignore_index=True)
    lineups = lineups.drop_duplicates(subset=["game_id", "player_id"])
    lineups["position_group"] = lineups["starting_position_name"].map(map_position_group)
    out = out.merge(
        lineups[["game_id", "player_id", "position_group"]],
        on=["game_id", "player_id"],
        how="left",
    )
    return out


def compute_position_weight(actions: pd.DataFrame) -> pd.Series:
    """Weight from POSITION_ACTION_WEIGHTS via (position_group, type_name)."""
    import socceraction.spadl as spadl

    named = spadl.add_names(actions)
    groups = actions.get("position_group")
    if groups is None:
        return pd.Series(1.0, index=actions.index)

    weights = np.ones(len(actions))
    type_names = named["type_name"].to_numpy()
    group_vals = groups.to_numpy()
    for i in range(len(actions)):
        grp = group_vals[i]
        if not isinstance(grp, str):
            continue
        table = POSITION_ACTION_WEIGHTS.get(grp)
        if table:
            weights[i] = table.get(type_names[i], 1.0)
    return pd.Series(
        np.clip(weights, POSITION_W_CLIP[0], POSITION_W_CLIP[1]), index=actions.index
    )


# ---------------------------------------------------------------------------
# Role weight
# ---------------------------------------------------------------------------


def compute_role_weight(actions: pd.DataFrame, role_state: Dict) -> pd.Series:
    """
    Weight > 1 when the action type is central to the player's role cluster
    (cluster rate above global rate). Complements v1 R, which rewards
    *unusual* actions; this rewards actions the role is responsible for.
    """
    import socceraction.spadl as spadl

    named = spadl.add_names(actions)
    rates = role_state["rates"]
    cluster_profiles = role_state["cluster_profiles"]
    feature_cols = role_state["feature_cols"]

    global_rates = rates[feature_cols].mean()
    player_cluster = rates["cluster"].to_dict()

    weights = np.ones(len(named))
    type_names = named["type_name"].to_numpy()
    player_ids = named["player_id"].to_numpy()

    for i in range(len(named)):
        pid = player_ids[i]
        if pd.isna(pid) or int(pid) not in player_cluster:
            continue
        col = f"rate_{type_names[i]}"
        if col not in cluster_profiles.columns:
            continue
        cluster = player_cluster[int(pid)]
        cluster_rate = float(cluster_profiles.loc[cluster, col])
        global_rate = float(global_rates.get(col, 0.0))
        if global_rate <= 1e-6:
            continue
        # sqrt dampens the ratio so the weight stays a mild adjustment
        weights[i] = np.sqrt(cluster_rate / global_rate)

    return pd.Series(np.clip(weights, ROLE_W_CLIP[0], ROLE_W_CLIP[1]), index=actions.index)


# ---------------------------------------------------------------------------
# Game-state weight
# ---------------------------------------------------------------------------


def compute_game_state_weight(actions: pd.DataFrame, games: pd.DataFrame) -> pd.Series:
    """
    Leverage weight: garbage time (|score_diff| >= 3) down, late close games
    (minute >= 85, |score_diff| <= 1) up, otherwise 1.0.
    """
    from skm.models.context import attach_game_context

    df = attach_game_context(actions, games)
    abs_diff = df["score_diff"].abs()

    w = np.ones(len(df))
    w = np.where(abs_diff >= 3, GAME_STATE_W_GARBAGE, w)
    w = np.where((df["minute_approx"] >= 85) & (abs_diff <= 1), GAME_STATE_W_LATE_CLOSE, w)
    return pd.Series(
        np.clip(w, GAME_STATE_W_CLIP[0], GAME_STATE_W_CLIP[1]), index=actions.index
    )


# ---------------------------------------------------------------------------
# Sequence weight
# ---------------------------------------------------------------------------

SHOT_TYPES = {"shot", "shot_penalty", "shot_freekick"}


def compute_sequence_weight(actions: pd.DataFrame) -> pd.Series:
    """
    Upweight non-shooting actions in same-team chains that end in a shot.

    A chain is a run of consecutive actions by the same team within a period,
    with no time gap above SEQUENCE_CHAIN_GAP_S. If a chain of at least
    SEQUENCE_MIN_CHAIN_LEN actions contains a shot, every earlier action in
    the chain gets SEQUENCE_SHOT_BOOST (the shot itself stays at 1.0).
    """
    import socceraction.spadl as spadl

    named = spadl.add_names(actions)
    df = named[["game_id", "period_id", "time_seconds", "team_id", "type_name"]].copy()
    df["orig_index"] = actions.index
    df = df.sort_values(["game_id", "period_id", "time_seconds"], kind="stable")

    new_chain = (
        (df["game_id"] != df["game_id"].shift())
        | (df["period_id"] != df["period_id"].shift())
        | (df["team_id"] != df["team_id"].shift())
        | ((df["time_seconds"] - df["time_seconds"].shift()) > SEQUENCE_CHAIN_GAP_S)
    )
    df["chain_id"] = new_chain.cumsum()
    df["is_shot"] = df["type_name"].isin(SHOT_TYPES)

    chain_has_shot = df.groupby("chain_id")["is_shot"].transform("any")
    chain_len = df.groupby("chain_id")["is_shot"].transform("size")

    boost = chain_has_shot & (chain_len >= SEQUENCE_MIN_CHAIN_LEN) & ~df["is_shot"]
    df["seq_w"] = np.where(boost, SEQUENCE_SHOT_BOOST, 1.0)

    return pd.Series(
        df.set_index("orig_index")["seq_w"].reindex(actions.index).fillna(1.0).to_numpy(),
        index=actions.index,
    )
