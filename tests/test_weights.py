import numpy as np
import pandas as pd
import pytest

from skm.config import (
    GAME_STATE_W_GARBAGE,
    GAME_STATE_W_LATE_CLOSE,
    SEQUENCE_SHOT_BOOST,
)
from skm.models.skm_combine import combine_adjusted_skm
from skm.models.weights import map_position_group

spadl = pytest.importorskip("socceraction.spadl")


def _spadl_type_id(name: str) -> int:
    types = spadl.actiontypes_df()
    return int(types.loc[types["type_name"] == name, "type_id"].iloc[0])


def _result_id(name: str) -> int:
    results = spadl.results_df()
    return int(results.loc[results["result_name"] == name, "result_id"].iloc[0])


def _bodypart_id() -> int:
    return int(spadl.bodyparts_df()["bodypart_id"].iloc[0])


def _base_actions(type_names, team_ids, time_seconds, player_ids=None):
    n = len(type_names)
    return pd.DataFrame(
        {
            "game_id": [1] * n,
            "period_id": [1] * n,
            "time_seconds": time_seconds,
            "team_id": team_ids,
            "player_id": player_ids if player_ids is not None else list(range(1, n + 1)),
            "type_id": [_spadl_type_id(t) for t in type_names],
            "result_id": [_result_id("success")] * n,
            "bodypart_id": [_bodypart_id()] * n,
        }
    )


def test_map_position_group():
    assert map_position_group("Goalkeeper") == "GK"
    assert map_position_group("Right Center Back") == "CB"
    assert map_position_group("Left Back") == "FB"
    assert map_position_group("Left Wing Back") == "FB"
    assert map_position_group("Center Defensive Midfield") == "DM"
    assert map_position_group("Left Center Midfield") == "CM"
    assert map_position_group("Center Attacking Midfield") == "AM"
    assert map_position_group("Left Attacking Midfield") == "W"
    assert map_position_group("Right Wing") == "W"
    assert map_position_group("Center Forward") == "ST"
    assert map_position_group("Substitute") is None
    assert map_position_group(None) is None


def test_position_weight_uses_prior_table():
    from skm.models.weights import compute_position_weight

    actions = _base_actions(
        ["shot", "shot", "tackle"],
        team_ids=[10, 10, 10],
        time_seconds=[10.0, 20.0, 30.0],
    )
    actions["position_group"] = ["ST", "CB", None]
    w = compute_position_weight(actions)
    assert w.iloc[0] == pytest.approx(1.2)  # ST shot boosted
    assert w.iloc[1] == pytest.approx(1.0)  # CB shot not in table
    assert w.iloc[2] == pytest.approx(1.0)  # unknown position → neutral


def test_sequence_weight_boosts_chain_ending_in_shot():
    from skm.models.weights import compute_sequence_weight

    # Team 10: pass → dribble → shot (one chain); team 20: isolated pass
    actions = _base_actions(
        ["pass", "dribble", "shot", "pass"],
        team_ids=[10, 10, 10, 20],
        time_seconds=[10.0, 15.0, 20.0, 25.0],
    )
    w = compute_sequence_weight(actions)
    assert w.iloc[0] == pytest.approx(SEQUENCE_SHOT_BOOST)
    assert w.iloc[1] == pytest.approx(SEQUENCE_SHOT_BOOST)
    assert w.iloc[2] == pytest.approx(1.0)  # the shot itself
    assert w.iloc[3] == pytest.approx(1.0)  # other team, no shot


def test_sequence_weight_no_shot_chain_is_neutral():
    from skm.models.weights import compute_sequence_weight

    actions = _base_actions(
        ["pass", "pass", "pass"],
        team_ids=[10, 10, 10],
        time_seconds=[10.0, 12.0, 14.0],
    )
    w = compute_sequence_weight(actions)
    assert (w == 1.0).all()


def test_game_state_weight_garbage_and_late_close():
    from skm.models.weights import compute_game_state_weight

    # Build a match where team 10 leads 3-0 (garbage) and one late close action.
    goal = _spadl_type_id("shot")
    passes = _spadl_type_id("pass")
    success = _result_id("success")
    bp = _bodypart_id()

    rows = []
    # three quick goals for team 10
    for t in (60.0, 120.0, 180.0):
        rows.append((1, 1, t, 10, 1, goal, success, bp))
    # action while 3-0 up (garbage time weight)
    rows.append((1, 1, 300.0, 10, 1, passes, success, bp))
    # separate match, 88th minute at 0-0 (late close weight)
    rows.append((2, 2, 43.5 * 60, 30, 2, passes, success, bp))
    # separate match, 20th minute at 0-0 (neutral)
    rows.append((3, 1, 20 * 60, 50, 3, passes, success, bp))

    actions = pd.DataFrame(
        rows,
        columns=[
            "game_id",
            "period_id",
            "time_seconds",
            "team_id",
            "player_id",
            "type_id",
            "result_id",
            "bodypart_id",
        ],
    )
    games = pd.DataFrame(
        {
            "game_id": [1, 2, 3],
            "home_team_id": [10, 30, 50],
            "away_team_id": [20, 40, 60],
        }
    ).set_index("game_id")

    w = compute_game_state_weight(actions, games)
    assert w.iloc[3] == pytest.approx(GAME_STATE_W_GARBAGE)
    assert w.iloc[4] == pytest.approx(GAME_STATE_W_LATE_CLOSE)
    assert w.iloc[5] == pytest.approx(1.0)


def test_combine_adjusted_skm_multiplies_weights():
    df = pd.DataFrame(
        {
            "skm": [0.1, 0.2],
            "position_weight": [1.2, 1.0],
            "role_weight": [1.1, 1.0],
            "game_state_weight": [0.7, 1.0],
            "sequence_weight": [1.15, 1.0],
        }
    )
    adj = combine_adjusted_skm(df)
    assert adj.iloc[0] == pytest.approx(0.1 * 1.2 * 1.1 * 0.7 * 1.15)
    assert adj.iloc[1] == pytest.approx(0.2)


def test_combine_adjusted_skm_missing_weights_falls_back_to_base():
    df = pd.DataFrame({"skm": [0.3, np.nan]})
    adj = combine_adjusted_skm(df)
    assert adj.iloc[0] == pytest.approx(0.3)
    assert adj.iloc[1] == pytest.approx(0.0)
