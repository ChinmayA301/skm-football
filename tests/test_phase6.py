import numpy as np
import pandas as pd
import pytest

from skm.models.phase6 import position_normalized_board


def _board_and_actions():
    # 10 STs scoring high, 10 DMs scoring low — classic positional tilt
    board = pd.DataFrame(
        {
            "player_id": range(20),
            "skm_v2_per90": np.r_[np.linspace(0.5, 0.9, 10), np.linspace(0.1, 0.3, 10)],
            "delta_p_per90": np.linspace(0.1, 0.4, 20),
            "progressive_per90": np.linspace(2, 8, 20),
        }
    )
    actions = pd.DataFrame(
        {
            "player_id": list(range(20)) * 3,
            "position_group": (["ST"] * 10 + ["DM"] * 10) * 3,
        }
    )
    return board, actions


def test_position_z_scores_center_each_group():
    board, actions = _board_and_actions()
    v3 = position_normalized_board(board, actions, min_group=5)
    for pos in ("ST", "DM"):
        grp = v3[v3["pos"] == pos]
        assert grp["skm_v3"].mean() == pytest.approx(0.0, abs=1e-9)
        assert (grp["pos_z_basis"] == "position").all()
    # Best DM outranks mid-table STs after normalization
    best_dm = v3[v3["pos"] == "DM"]["skm_v3"].max()
    median_st = v3[v3["pos"] == "ST"]["skm_v3"].median()
    assert best_dm > median_st


def test_small_group_falls_back_to_global():
    board, actions = _board_and_actions()
    v3 = position_normalized_board(board, actions, min_group=15)  # both groups too small
    assert (v3["pos_z_basis"] == "global").all()
    assert v3["skm_v3"].mean() == pytest.approx(0.0, abs=1e-9)


def test_missing_position_uses_global_basis():
    board, actions = _board_and_actions()
    actions.loc[actions["player_id"] == 0, "position_group"] = None
    v3 = position_normalized_board(board, actions, min_group=5)
    row = v3[v3["player_id"] == 0].iloc[0]
    assert row["pos_z_basis"] == "global"
