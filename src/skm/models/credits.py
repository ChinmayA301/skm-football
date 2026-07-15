"""Phase 5b: moment_value roll-up and per-player moment credits.

Pipeline:

1. skm_chance = existing action-level SKM (v1 formula)
2. skm_control = structural boost layer (see skm.models.control)
3. action_value = skm_chance + skm_control
4. moment_value = Σ action_value over each moment
5. player credit per moment:

       credit = α · own_action_value + (1 − α) · involvement_share · moment_value

   with α = MOMENT_CREDIT_ALPHA. α = 1 reduces to pure individual value;
   α = 0 shares every moment purely by touch share. The blend keeps the
   individual skill signal while crediting involvement in successful moments.

6. Provisional v2 leaderboard: skm_v2_per90 = Σ credits per 90.

The CLI prints the Phase 6 target checks (ρ vs ΔP, ρ vs progressive per90)
for v1 and v2 side by side. Hitting the targets is a Phase 6 concern —
this module reports honestly, it does not tune.
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
    MOMENT_CREDIT_ALPHA,
    PLAYER_CREDITS_PARQUET,
    PLAYER_SKM_V2_PARQUET,
)
from skm.models.control import compute_skm_control
from skm.models.moments import build_moments, infer_home_teams

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def build_player_credits(
    actions: pd.DataFrame,
    alpha: float = MOMENT_CREDIT_ALPHA,
) -> tuple:
    """
    Return (credits_df, segmented_actions).

    credits_df has one row per (moment_id, player_id) with own_value,
    involvement_share, moment_value, and the blended credit.
    """
    home_teams = infer_home_teams(actions)

    ctrl = compute_skm_control(actions, home_teams)
    actions = actions.copy()
    actions["skm_control"] = ctrl["skm_control"].to_numpy()
    actions["is_progressive"] = ctrl["is_progressive"].to_numpy()
    actions["action_value"] = actions["skm"].fillna(0) + actions["skm_control"]

    _, involvement, seg = build_moments(actions, home_teams=home_teams)

    moment_value = seg.groupby("moment_id")["action_value"].sum().rename("moment_value")
    own = (
        seg[seg["player_id"].notna()]
        .groupby(["moment_id", "player_id"])["action_value"]
        .sum()
        .rename("own_value")
        .reset_index()
    )

    credits = involvement.merge(own, on=["moment_id", "player_id"], how="left")
    credits["own_value"] = credits["own_value"].fillna(0)
    credits = credits.merge(moment_value, on="moment_id", how="left")
    credits["credit"] = (
        alpha * credits["own_value"]
        + (1.0 - alpha) * credits["involvement_share"] * credits["moment_value"]
    )
    return credits, seg


def v2_leaderboard(
    credits: pd.DataFrame,
    seg: pd.DataFrame,
    min_actions: int = 400,
) -> pd.DataFrame:
    """Per-player v2 (moment-credit) totals, with v1 columns for comparison."""
    per_player = (
        seg[seg["player_id"].notna()]
        .groupby("player_id")
        .agg(
            skm_v1_total=("skm", "sum"),
            delta_p_total=("delta_p", "sum"),
            n_actions=("skm", "size"),
            progressive_total=("is_progressive", "sum"),
        )
        .reset_index()
    )
    credit_totals = credits.groupby("player_id")["credit"].sum().rename("skm_v2_total")
    board = per_player.merge(credit_totals, on="player_id", how="left")
    board["skm_v2_total"] = board["skm_v2_total"].fillna(0)

    board = board[board["n_actions"] >= min_actions]
    actions_per_minute = board["n_actions"].sum() / max(len(seg) / 90.0, 1.0)
    board["minutes_est"] = board["n_actions"] / max(actions_per_minute / 90.0, 1e-6)

    for col in ("skm_v1", "skm_v2", "delta_p", "progressive"):
        board[f"{col}_per90"] = board[f"{col}_total"] / board["minutes_est"] * 90.0

    return board.sort_values("skm_v2_per90", ascending=False)


def phase6_checks(board: pd.DataFrame) -> pd.DataFrame:
    """Spearman correlations against the Phase 6 targets, v1 vs v2."""
    rows = []
    for version in ("skm_v1", "skm_v2"):
        rows.append(
            {
                "metric": version,
                "rho_delta_p": board[f"{version}_per90"].corr(
                    board["delta_p_per90"], method="spearman"
                ),
                "rho_progressive": board[f"{version}_per90"].corr(
                    board["progressive_per90"], method="spearman"
                ),
            }
        )
    checks = pd.DataFrame(rows)
    checks["target_rho_delta_p_lt_0.99"] = checks["rho_delta_p"] < 0.99
    checks["target_rho_progressive_gt_0"] = checks["rho_progressive"] > 0
    return checks


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Build moment credits + v2 leaderboard (Phase 5b)")
    parser.add_argument("--actions-input", default=str(ACTIONS_SCORED_PARQUET))
    parser.add_argument("--credits-output", default=str(PLAYER_CREDITS_PARQUET))
    parser.add_argument("--leaderboard-output", default=str(PLAYER_SKM_V2_PARQUET))
    parser.add_argument("--alpha", type=float, default=MOMENT_CREDIT_ALPHA)
    parser.add_argument("--min-actions", type=int, default=400)
    args = parser.parse_args(argv)

    actions = pd.read_parquet(args.actions_input)
    logger.info("Loaded %s scored actions (%s games)", len(actions), actions["game_id"].nunique())

    credits, seg = build_player_credits(actions, alpha=args.alpha)
    board = v2_leaderboard(credits, seg, min_actions=args.min_actions)

    for path, frame, label in [
        (Path(args.credits_output), credits, "moment credits"),
        (Path(args.leaderboard_output), board, "v2 leaderboard rows"),
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(path, index=False)
        logger.info("Wrote %s %s → %s", len(frame), label, path)

    print(f"\nPhase 6 target checks (alpha={args.alpha}, min_actions={args.min_actions}):")
    print(phase6_checks(board).to_string(index=False))

    print("\nTop 10 by skm_v2_per90:")
    cols = ["player_id", "skm_v2_per90", "skm_v1_per90", "delta_p_per90", "progressive_per90"]
    print(board[cols].head(10).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
