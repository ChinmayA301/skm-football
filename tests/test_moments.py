import pandas as pd
import pytest

from skm.config import MOMENT_MAX_ACTIONS

spadl = pytest.importorskip("socceraction.spadl")

from skm.models.moments import (  # noqa: E402
    build_moments,
    infer_home_teams,
    segment_moments,
)


def _type_id(name: str) -> int:
    types = spadl.actiontypes_df()
    return int(types.loc[types["type_name"] == name, "type_id"].iloc[0])


def _result_id(name: str) -> int:
    results = spadl.results_df()
    return int(results.loc[results["result_name"] == name, "result_id"].iloc[0])


def _actions(rows):
    """rows: list of dicts with partial fields; fill SPADL defaults."""
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
    }
    out = []
    for i, r in enumerate(rows):
        row = {**defaults, **r}
        row.setdefault("time_seconds", float(i * 5))
        row.setdefault("action_id", i)
        out.append(row)
    return pd.DataFrame(out)


def test_team_change_starts_new_moment():
    df = _actions([{"team_id": 10}, {"team_id": 10}, {"team_id": 20}, {"team_id": 20}])
    seg = segment_moments(df)
    assert seg["moment_id"].nunique() == 2
    assert seg.iloc[2]["start_reason"] == "team_change"


def test_time_gap_starts_new_moment():
    df = _actions(
        [
            {"time_seconds": 0.0},
            {"time_seconds": 5.0},
            {"time_seconds": 60.0},  # 55s gap
        ]
    )
    seg = segment_moments(df)
    assert seg["moment_id"].nunique() == 2
    assert seg.iloc[2]["start_reason"] == "gap"


def test_dead_ball_starts_new_moment():
    df = _actions(
        [
            {},
            {},
            {"type_id": _type_id("throw_in")},
            {},
        ]
    )
    seg = segment_moments(df)
    assert seg["moment_id"].nunique() == 2
    assert seg.iloc[2]["start_reason"] == "set_piece"


def test_length_cap_splits_moment():
    n = MOMENT_MAX_ACTIONS + 5
    df = _actions([{"time_seconds": float(i)} for i in range(n)])
    seg = segment_moments(df)
    assert seg["moment_id"].nunique() == 2
    sizes = seg.groupby("moment_id").size().tolist()
    assert sizes == [MOMENT_MAX_ACTIONS, 5]
    # continuation is flagged as a cap split
    assert (seg["start_reason"] == "cap").sum() == 1


def test_transition_vs_open_play_classification():
    home = {1: 10}
    # Team 20 possession, then team 10 regains and moves 30m forward fast
    fast = _actions(
        [
            {"team_id": 20, "start_x": 60, "end_x": 55},
            {"team_id": 10, "start_x": 40, "end_x": 60},
            {"team_id": 10, "start_x": 60, "end_x": 70},
        ]
    )
    moments, _, _ = build_moments(fast, home_teams=home)
    regain = moments[moments["start_reason"] == "team_change"].iloc[0]
    assert regain["moment_type"] == "transition"

    # Same regain but sideways/backward → open_play
    slow = _actions(
        [
            {"team_id": 20, "start_x": 60, "end_x": 55},
            {"team_id": 10, "start_x": 40, "end_x": 42},
            {"team_id": 10, "start_x": 42, "end_x": 41},
        ]
    )
    moments, _, _ = build_moments(slow, home_teams=home)
    regain = moments[moments["start_reason"] == "team_change"].iloc[0]
    assert regain["moment_type"] == "open_play"


def test_away_team_transition_uses_flipped_direction():
    # Team 20 is away (attacks right→left): decreasing x is forward
    home = {1: 10}
    df = _actions(
        [
            {"team_id": 10, "start_x": 60, "end_x": 65},
            {"team_id": 20, "start_x": 80, "end_x": 60},
            {"team_id": 20, "start_x": 60, "end_x": 50},
        ]
    )
    moments, _, _ = build_moments(df, home_teams=home)
    regain = moments[moments["start_reason"] == "team_change"].iloc[0]
    assert regain["moment_type"] == "transition"


def test_involvement_shares_sum_to_one():
    df = _actions(
        [
            {"player_id": 1},
            {"player_id": 2},
            {"player_id": 2},
            {"player_id": 3, "team_id": 20},
        ]
    )
    _, credits, _ = build_moments(df, home_teams={1: 10})
    sums = credits.groupby("moment_id")["involvement_share"].sum()
    assert (abs(sums - 1.0) < 1e-9).all()
    first = credits[credits["moment_id"] == credits["moment_id"].min()]
    assert first.set_index("player_id")["involvement_share"].loc[2] == pytest.approx(2 / 3)


def test_score_diff_at_moment_start():
    shot = _type_id("shot")
    df = _actions(
        [
            {"team_id": 10},
            {"team_id": 10, "type_id": shot},  # goal for team 10
            {"team_id": 20, "time_seconds": 40.0},  # kickoff-ish, new moment
        ]
    )
    moments, _, _ = build_moments(df, home_teams={1: 10})
    conceding = moments[moments["team_id"] == 20].iloc[0]
    assert conceding["score_diff_start"] == -1
    assert bool(moments[moments["team_id"] == 10].iloc[0]["contains_goal"]) is True


def test_infer_home_teams_from_shot_direction():
    shot = _type_id("shot")
    fail = _result_id("fail")
    df = _actions(
        [
            {"team_id": 10, "type_id": shot, "result_id": fail, "end_x": 115.0},
            {"team_id": 20, "type_id": shot, "result_id": fail, "end_x": 5.0},
        ]
    )
    assert infer_home_teams(df) == {1: 10}
