"""Phase 6: position-normalized SKM (skm_v3).

The structural problem, characterized on 233 players / 216 matches: both
v1 and v2 concentrate value in shot-adjacent actions, so ρ(SKM,
progressive/90) is negative — attackers dominate any cross-position table.
Parameter tuning cannot fix this (documented sensitivity analysis in
ROADMAP); the pre-registered structural change is to compare players
*within* position groups.

skm_v3 = z-score of skm_v2_per90 within the player's primary position
group (modal position_group across their actions). Groups smaller than
MIN_GROUP fall back to the global z-score, flagged in `pos_z_basis`.

This changes the metric's meaning — v3 answers "how good is this player
relative to their positional peers?", which is the question scouts
actually ask. It is dimensionless by construction.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

from skm.config import (
    ACTIONS_SCORED_PARQUET,
    DATA_PROCESSED,
    PLAYER_SKM_V2_PARQUET,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MIN_GROUP = 8
PLAYER_SKM_V3_PARQUET = DATA_PROCESSED / "player_skm_v3.parquet"


def primary_positions(actions: pd.DataFrame) -> pd.Series:
    """player_id → modal position_group (NaN when never observed)."""
    pos = actions.dropna(subset=["player_id"]).groupby("player_id")["position_group"]
    return pos.agg(lambda s: s.mode().iloc[0] if s.notna().any() else None)


def position_normalized_board(
    board: pd.DataFrame,
    actions: pd.DataFrame,
    metric: str = "skm_v2_per90",
    min_group: int = MIN_GROUP,
) -> pd.DataFrame:
    """Add `pos`, `skm_v3` (position z-score of `metric`) and `pos_z_basis`."""
    out = board.copy()
    out["pos"] = out["player_id"].map(primary_positions(actions))

    g_mean, g_std = out[metric].mean(), out[metric].std(ddof=0) or 1.0
    out["skm_v3"] = (out[metric] - g_mean) / g_std
    out["pos_z_basis"] = "global"

    for pos, grp in out.groupby("pos"):
        if len(grp) < min_group:
            continue
        std = grp[metric].std(ddof=0)
        if not std:
            continue
        out.loc[grp.index, "skm_v3"] = (grp[metric] - grp[metric].mean()) / std
        out.loc[grp.index, "pos_z_basis"] = "position"

    return out.sort_values("skm_v3", ascending=False)


def phase6_checks_v3(board: pd.DataFrame) -> pd.DataFrame:
    """Phase 6 targets for raw v2 and position-normalized v3, side by side."""
    rows = []
    for metric in ("skm_v2_per90", "skm_v3"):
        rows.append(
            {
                "metric": metric,
                "rho_delta_p": board[metric].corr(board["delta_p_per90"], method="spearman"),
                "rho_progressive": board[metric].corr(
                    board["progressive_per90"], method="spearman"
                ),
            }
        )
    checks = pd.DataFrame(rows)
    checks["target_rho_delta_p_lt_0.99"] = checks["rho_delta_p"] < 0.99
    checks["target_rho_progressive_gt_0"] = checks["rho_progressive"] > 0
    return checks


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 6: position-normalized SKM (v3)")
    parser.add_argument("--board-input", default=str(PLAYER_SKM_V2_PARQUET))
    parser.add_argument("--actions-input", default=str(ACTIONS_SCORED_PARQUET))
    parser.add_argument("--output", default=str(PLAYER_SKM_V3_PARQUET))
    args = parser.parse_args(argv)

    board = pd.read_parquet(args.board_input)
    actions = pd.read_parquet(args.actions_input)

    v3 = position_normalized_board(board, actions)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    v3.to_parquet(out, index=False)
    logger.info("Wrote %s players → %s", len(v3), out)

    print("\nPhase 6 target checks (v2 raw vs v3 position-normalized):")
    print(phase6_checks_v3(v3).to_string(index=False))
    print("\nPer-position group sizes:")
    print(v3["pos"].value_counts(dropna=False).to_string())
    print("\nTop 3 per position (skm_v3):")
    top = v3[v3["pos_z_basis"] == "position"].groupby("pos").head(3)
    print(top[["player_id", "pos", "skm_v3", "skm_v2_per90", "progressive_per90"]]
          .sort_values(["pos", "skm_v3"], ascending=[True, False]).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
