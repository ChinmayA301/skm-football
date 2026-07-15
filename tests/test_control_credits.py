import pandas as pd
import pytest

from skm.config import (
    CONTROL_PRESS_MULT,
    CONTROL_PROG_MULT,
    CONTROL_ZONE_MULT,
)

spadl = pytest.importorskip("socceraction.spadl")

from skm.models.control import compute_skm_control  # noqa: E402
from skm.models.credits import build_player_credits, v2_leaderboard  # noqa: E402


def _type_id(name: str) -> int:
    types = spadl.actiontypes_df()
    return int(types.loc[types["type_name"] == name, "type_id"].iloc[0])


def _result_id(name: str) -> int:
    results = spadl.results_df()
    return int(results.loc[results["result_name"] == name, "result_id"].iloc[0])


def _actions(rows):
    defaults = {
        "game_id": 1,
        "period_id": 1,
        "team_id": 10,
        "player_id": 1,
        "type_id": _type_id("pass"),
        "result_id": _result_id("success"),
        "bodypart_id": int(spadl.bodyparts_df()["bodypart_id"].iloc[0]),
        "start_x": 50.0,
        "start_y": 40.0,
        "end_x": 55.0,
        "end_y": 40.0,
        "delta_p": 0.01,
        "skm": 0.01,
        "under_pressure": False,
    }
    out = []
    for i, r in enumerate(rows):
        row = {**defaults, **r}
        row.setdefault("time_seconds", float(i * 5))
        row.setdefault("action_id", i)
        out.append(row)
    return pd.DataFrame(out)


HOME = {1: 10}
UNIT = 0.01  # all synthetic delta_p are 0.01, so median positive ΔP = 0.01


def test_progressive_bonus_home_direction():
    df = _actions([{"start_x": 40.0, "end_x": 60.0}])
    ctrl = compute_skm_control(df, home_teams=HOME)
    assert bool(ctrl["is_progressive"].iloc[0]) is True
    assert ctrl["skm_control"].iloc[0] == pytest.approx(CONTROL_PROG_MULT * UNIT)


def test_progressive_bonus_away_direction_flipped():
    df = _actions([{"team_id": 20, "start_x": 80.0, "end_x": 60.0}])
    ctrl = compute_skm_control(df, home_teams=HOME)
    assert bool(ctrl["is_progressive"].iloc[0]) is True
    # +x movement by the away team is backward, not progressive
    df2 = _actions([{"team_id": 20, "start_x": 60.0, "end_x": 80.0}])
    ctrl2 = compute_skm_control(df2, home_teams=HOME)
    assert bool(ctrl2["is_progressive"].iloc[0]) is False


def test_failed_action_gets_no_bonus():
    df = _actions([{"start_x": 40.0, "end_x": 60.0, "result_id": _result_id("fail")}])
    ctrl = compute_skm_control(df, home_teams=HOME)
    assert ctrl["skm_control"].iloc[0] == pytest.approx(0.0)


def test_pressure_resistance_bonus():
    df = _actions([{"under_pressure": True}])  # short pass, not progressive
    ctrl = compute_skm_control(df, home_teams=HOME)
    assert ctrl["skm_control"].iloc[0] == pytest.approx(CONTROL_PRESS_MULT * UNIT)


def test_defensive_zone_bonus_own_third():
    tackle = _type_id("tackle")
    inside = _actions([{"type_id": tackle, "start_x": 20.0}])
    outside = _actions([{"type_id": tackle, "start_x": 60.0}])
    assert compute_skm_control(inside, home_teams=HOME)["skm_control"].iloc[
        0
    ] == pytest.approx(CONTROL_ZONE_MULT * UNIT)
    assert compute_skm_control(outside, home_teams=HOME)["skm_control"].iloc[
        0
    ] == pytest.approx(0.0)


def test_credit_alpha_blend_and_conservation():
    # One moment, two players, no structural bonuses (short sideways passes)
    df = _actions(
        [
            {"player_id": 1, "skm": 0.02, "end_x": 50.0, "end_y": 45.0},
            {"player_id": 2, "skm": 0.01, "end_x": 50.0, "end_y": 40.0},
            {"player_id": 2, "skm": 0.03, "end_x": 50.0, "end_y": 35.0},
        ]
    )
    alpha = 0.7
    credits, _ = build_player_credits(df, alpha=alpha)
    assert len(credits) == 2
    mv = 0.06
    p1 = credits.set_index("player_id").loc[1]
    assert p1["credit"] == pytest.approx(alpha * 0.02 + (1 - alpha) * (1 / 3) * mv)
    # Credits conserve moment value when every action has a player
    assert credits["credit"].sum() == pytest.approx(mv)


def test_v2_leaderboard_columns():
    df = _actions(
        [{"player_id": p, "skm": 0.01, "time_seconds": float(i * 5)} for i, p in enumerate([1, 1, 2, 2])]
    )
    credits, seg = build_player_credits(df, alpha=0.7)
    board = v2_leaderboard(credits, seg, min_actions=0)
    for col in ("skm_v1_per90", "skm_v2_per90", "delta_p_per90", "progressive_per90"):
        assert col in board.columns
    assert len(board) == 2
