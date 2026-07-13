"""Gate 2: propagate D_360 through the full SKM stack and report rank changes.

VAEP (ΔP), C, R, and the v1.5 weights are unchanged — only D is replaced by
the geometry-aware D_360 — so this recomputes exactly, with no retraining:

    skm_360          (already in actions_360.parquet)
    adjusted_skm_360 = skm_360 × position/role/game-state/sequence weights
    v1 leaderboard   with D_360
    v2 (moment credits) with D_360, incl. Phase 6 checks

Outputs go to *_360.parquet files; the base parquets are untouched until
the rank-change review is documented (that's the gate).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skm.config import ACTIONS_360_PARQUET, DATA_PROCESSED, GAMES_PARQUET  # noqa: E402
from skm.models.credits import build_player_credits, phase6_checks, v2_leaderboard  # noqa: E402
from skm.models.skm_combine import player_leaderboard  # noqa: E402

WEIGHT_COLS = ["position_weight", "role_weight", "game_state_weight", "sequence_weight"]


def main() -> int:
    actions = pd.read_parquet(ACTIONS_360_PARQUET)
    games = pd.read_parquet(GAMES_PARQUET).set_index("game_id")
    names = (
        pd.read_parquet(DATA_PROCESSED / "player_names.parquet")
        .set_index("player_id")["player_name"]
    )

    adj = actions["skm_360"].fillna(0)
    for col in WEIGHT_COLS:
        if col in actions.columns:
            adj = adj * actions[col].fillna(1.0)
    actions["adjusted_skm_360"] = adj

    # v1 leaderboards: baseline D vs D_360
    base = player_leaderboard(actions, games)
    swapped = actions.copy()
    swapped["skm"] = swapped["skm_360"]
    swapped["adjusted_skm"] = swapped["adjusted_skm_360"]
    board_360 = player_leaderboard(swapped, games)
    board_360.to_parquet(DATA_PROCESSED / "player_leaderboard_360.parquet", index=False)

    cmp = base[["player_id", "skm_per90"]].merge(
        board_360[["player_id", "skm_per90"]].rename(columns={"skm_per90": "skm360_per90"}),
        on="player_id",
    )
    cmp["player"] = cmp["player_id"].map(names)
    cmp["rank_base"] = cmp["skm_per90"].rank(ascending=False)
    cmp["rank_360"] = cmp["skm360_per90"].rank(ascending=False)
    cmp["rank_change"] = cmp["rank_base"] - cmp["rank_360"]

    rho = cmp["skm_per90"].corr(cmp["skm360_per90"], method="spearman")
    print(f"\nGate 2 — D_360 propagation ({len(cmp)} players ≥400 actions)")
    print(f"rank correlation base vs 360: ρ = {rho:.3f}")
    show = ["player", "rank_base", "rank_360", "rank_change"]
    print("\nBiggest risers with real defender geometry:")
    print(cmp.sort_values("rank_change", ascending=False)[show].head(8).to_string(index=False))
    print("\nBiggest fallers:")
    print(cmp.sort_values("rank_change")[show].head(8).to_string(index=False))

    # v2 (moment credits) with D_360
    credits, seg = build_player_credits(swapped)
    v2_360 = v2_leaderboard(credits, seg)
    v2_360.to_parquet(DATA_PROCESSED / "player_skm_v2_360.parquet", index=False)
    print("\nPhase 6 checks with D_360:")
    print(phase6_checks(v2_360).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
