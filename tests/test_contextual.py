import pandas as pd
import pytest

from skm.models.contextual import _difficulty_mult, _game_state_mult

spadl = pytest.importorskip("socceraction.spadl")

from skm.models.contextual import pressure_value  # noqa: E402


def test_goal_difficulty_rewards_hard_finishes():
    # a low-xG goal is worth more than a high-xG tap-in
    assert _difficulty_mult("goal", 0.05) > _difficulty_mult("goal", 0.85)
    assert _difficulty_mult("goal", 0.05) > 1.0
    assert _difficulty_mult("goal", 0.85) < 1.0


def test_save_difficulty_scales_with_shot_quality():
    assert _difficulty_mult("keeper_save", 0.8) > _difficulty_mult("keeper_save", 0.1)


def test_game_state_late_comeback_up_garbage_down():
    late_comeback = _game_state_mult(88, -1, True)  # 88', trailing, team wins
    garbage = _game_state_mult(20, 4, True)  # 20', 4-0 up
    level = _game_state_mult(60, 0, False)
    assert late_comeback > level > garbage
    assert garbage < 1.0
    assert late_comeback > 1.5


def test_low_xg_comeback_goal_far_outweighs_high_xg_blowout():
    lo = _difficulty_mult("goal", 0.05) * _game_state_mult(88, -1, True)
    hi = _difficulty_mult("goal", 0.85) * _game_state_mult(20, 4, True)
    assert lo > 4 * hi  # the founding example: hard late winner >> easy blowout goal


def _type_id(name):
    t = spadl.actiontypes_df()
    return int(t.loc[t["type_name"] == name, "type_id"].iloc[0])


def test_pressure_value_rewards_success_under_pressure():
    bp = int(spadl.bodyparts_df()["bodypart_id"].iloc[0])
    succ = int(spadl.results_df().loc[spadl.results_df().result_name == "success", "result_id"].iloc[0])
    fail = int(spadl.results_df().loc[spadl.results_df().result_name == "fail", "result_id"].iloc[0])
    rows = [
        # successful pass under heavy pressure (defender 1.5m) → high value
        {"result_id": succ, "under_pressure": True, "nearest_def_m": 1.5, "type_id": _type_id("pass")},
        # successful pass in space (defender 9m) → ~0
        {"result_id": succ, "under_pressure": False, "nearest_def_m": 9.0, "type_id": _type_id("pass")},
        # failed pass under pressure → 0
        {"result_id": fail, "under_pressure": True, "nearest_def_m": 1.5, "type_id": _type_id("pass")},
    ]
    df = pd.DataFrame(
        [
            {"game_id": 1, "period_id": 1, "time_seconds": float(i), "team_id": 10,
             "player_id": 1, "start_x": 50, "start_y": 40, "end_x": 55, "end_y": 40,
             "bodypart_id": bp, **r}
            for i, r in enumerate(rows)
        ]
    )
    pv = pressure_value(df)
    assert pv.iloc[0] > 0.5  # under real pressure, succeeded
    assert pv.iloc[1] == pytest.approx(0.0)  # in space
    assert pv.iloc[2] == pytest.approx(0.0)  # failed
