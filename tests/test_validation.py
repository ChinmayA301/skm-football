"""Tests for validation helpers (no parquet I/O)."""

import numpy as np
import pandas as pd
import pytest

from skm.viz.validation import build_validation_table, spearman_matrix


def test_spearman_matrix_identity():
    df = pd.DataFrame({"a": [1, 2, 3, 4, 5], "b": [1, 2, 3, 4, 5]})
    rho, _ = spearman_matrix(df, ["a", "b"])
    assert rho.loc["a", "b"] == pytest.approx(1.0)


def test_spearman_pair_from_dataframe_column():
    """Regression: 2-D column slice must not return a correlation matrix."""
    from skm.viz.validation import _spearman_pair

    dup = pd.DataFrame({"x": [1, 2, 3, 4, 5, 6], "y": [2, 3, 4, 5, 6, 7]})
    two_col = dup[["x", "x"]]
    r, p = _spearman_pair(two_col, dup["y"])
    assert isinstance(r, float)
    assert np.isfinite(r)


def test_build_validation_table_merge():
    board = pd.DataFrame(
        {
            "player_id": [1.0, 2.0],
            "player": ["A", "B"],
            "skm_per90": [0.5, 0.3],
            "delta_p_per90": [0.4, 0.2],
            "xt_per90": [0.1, 0.1],
            "n_actions": [500, 500],
        }
    )
    events = pd.DataFrame(
        {
            "player_id": [1.0] * 500 + [2.0] * 500,
            "event_type": ["Shot"] * 10 + ["Pass"] * 990,
            "outcome": ["Goal"] * 10 + [None] * 990,
            "progressive": [True] * 200 + [False] * 800,
            "pass_goal_assist": [False] * 1000,
        }
    )
    val = build_validation_table(board, events, min_actions=400)
    assert len(val) == 2
    assert "goals_per90" in val.columns
    assert val.loc[val["player_id"] == 1.0, "goals"].iloc[0] == 10
