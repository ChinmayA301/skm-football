import pandas as pd
import pytest

from skm.models.freeze_frame import compute_frame_features


def _frame(event_id, players):
    """players: list of (teammate, actor, x, y)."""
    return pd.DataFrame(
        [
            {"id": event_id, "teammate": tm, "actor": ac, "fx": x, "fy": y}
            for tm, ac, x, y in players
        ]
    )


def test_pressure_geometry_basic():
    frames = _frame(
        "e1",
        [
            (True, True, 60.0, 40.0),  # actor
            (False, False, 63.0, 40.0),  # defender 3m
            (False, False, 68.0, 40.0),  # defender 8m, ahead
            (False, False, 40.0, 40.0),  # defender 20m behind
            (True, False, 55.0, 40.0),  # teammate (ignored)
        ],
    )
    f = compute_frame_features(frames).iloc[0]
    assert f["nearest_def_m"] == pytest.approx(3.0)
    assert f["n_def_5m"] == 1
    assert f["n_def_10m"] == 2
    assert f["n_def_ahead"] == 2  # x > 60 for two defenders
    assert f["n_visible"] == 5


def test_no_opponents_in_frame():
    frames = _frame("e2", [(True, True, 60.0, 40.0), (True, False, 50.0, 40.0)])
    f = compute_frame_features(frames).iloc[0]
    assert f["n_def_5m"] == 0
    assert f["nearest_def_m"] == pytest.approx(30.0)  # open-space sentinel


def test_event_without_actor_is_skipped():
    frames = _frame("e3", [(False, False, 60.0, 40.0)])
    out = compute_frame_features(frames)
    assert len(out) == 0
