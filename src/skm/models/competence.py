"""SKM v4 — position-relative competence.

The founding SKM thesis was to measure **position-specific success and
competence**, not to reward attacking intent. v1–v3 drifted from that: the
value backbone is VAEP ΔP (an attacking/scoring-probability signal), and the
later layers (D/C/R multipliers, position priors, position z-scoring) only
scale or re-rank that offense-skewed quantity. So a ball-winning midfielder
whose actions carry low ΔP stays buried no matter how you normalise.

v4 changes the *baseline*, not the scaling. Each action is scored by how it
compares to what a **positional peer** does with the **same action type** —
so competence, not raw attacking value, is the unit:

    z(action) = (value − mean_value[position, action_type])
                / std_value[position, action_type]

A defensive midfielder's interception is judged against other defensive
midfielders' interceptions; a striker's shot against other strikers' shots.
Doing your position's job better than peers scores well even when the
absolute ΔP is small; a league-average striker's shots score ~0 because
they are exactly what a striker is expected to produce.

Per-action z-scores are shrunk toward 0 by sample size (a player needs
enough of an action type before their deviation counts), then aggregated to
a per-player competence rating that is position-fair by construction.

`value_col` defaults to `skm` but can be `delta_p` or any per-action value.
Requires a `position_group` column on the actions (see
`skm.models.weights.map_position_group` / `attach_player_positions`).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from skm.config import ACTIONS_SCORED_PARQUET, DATA_PROCESSED

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PLAYER_COMPETENCE_PARQUET = DATA_PROCESSED / "player_competence.parquet"

SHRINKAGE_K = 20  # a player needs ~K actions of a type before full weight
MIN_BUCKET = 30  # (position, action_type) buckets smaller than this are pooled


def _action_type_names(actions: pd.DataFrame) -> pd.Series:
    import socceraction.spadl as spadl

    return spadl.add_names(actions)["type_name"]


def competence_scores(
    actions: pd.DataFrame,
    value_col: str = "skm",
    min_actions: int = 400,
    shrinkage_k: int = SHRINKAGE_K,
) -> pd.DataFrame:
    """
    Per-player position-relative competence.

    Returns one row per player: competence (shrunk mean action z-score),
    n_actions, pos, and the raw per-action z sum for reference.
    """
    df = actions.copy()
    df["type_name"] = _action_type_names(actions).to_numpy()
    df = df[df["player_id"].notna() & df["position_group"].notna()].copy()
    df["val"] = df[value_col].fillna(0.0)

    # Baseline per (position, action_type): mean & std over ALL players.
    grp = df.groupby(["position_group", "type_name"])["val"]
    stats = grp.agg(["mean", "std", "size"]).rename(
        columns={"mean": "b_mean", "std": "b_std", "size": "b_n"}
    )
    # Pool tiny buckets to the position-level baseline to avoid noise.
    pos_stats = df.groupby("position_group")["val"].agg(["mean", "std"]).rename(
        columns={"mean": "p_mean", "std": "p_std"}
    )
    stats = stats.join(pos_stats, on="position_group")
    small = stats["b_n"] < MIN_BUCKET
    stats.loc[small, "b_mean"] = stats.loc[small, "p_mean"]
    stats.loc[small, "b_std"] = stats.loc[small, "p_std"]

    df = df.join(stats[["b_mean", "b_std"]], on=["position_group", "type_name"])
    std = df["b_std"].replace(0, np.nan)
    df["z"] = ((df["val"] - df["b_mean"]) / std).fillna(0.0)
    # clip extreme single-action z to keep the aggregate robust
    df["z"] = df["z"].clip(-5, 5)

    # Aggregate per (player, action_type): mean z, shrunk by count.
    pt = df.groupby(["player_id", "type_name"]).agg(
        z_mean=("z", "mean"), n=("z", "size"), pos=("position_group", "first")
    )
    pt["z_shrunk"] = pt["z_mean"] * (pt["n"] / (pt["n"] + shrinkage_k))

    # Player competence: volume-weighted mean of per-type shrunk z, weighted by
    # how much the player actually does each type (so it reflects their real job).
    def _agg(g):
        w = g["n"]
        return pd.Series(
            {
                "competence": float(np.average(g["z_shrunk"], weights=w)),
                "n_actions": int(w.sum()),
                "pos": g["pos"].iloc[0],
            }
        )

    board = pt.groupby("player_id").apply(_agg, include_groups=False).reset_index()
    board = board[board["n_actions"] >= min_actions].copy()
    board["competence_rank"] = board["competence"].rank(ascending=False)
    return board.sort_values("competence", ascending=False)


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="SKM v4 position-relative competence")
    parser.add_argument("--actions-input", default=str(ACTIONS_SCORED_PARQUET))
    parser.add_argument("--output", default=str(PLAYER_COMPETENCE_PARQUET))
    parser.add_argument("--value-col", default="skm")
    parser.add_argument("--min-actions", type=int, default=400)
    args = parser.parse_args(argv)

    actions = pd.read_parquet(args.actions_input)
    board = competence_scores(actions, value_col=args.value_col, min_actions=args.min_actions)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    board.to_parquet(args.output, index=False)
    logger.info("Wrote competence for %s players → %s", len(board), args.output)
    print("\nTop 15 by competence:")
    print(board.head(15).to_string(index=False))
    print("\nPer-position representation in top 40:")
    print(board.head(40)["pos"].value_counts().to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
