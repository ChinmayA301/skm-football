import json

import pandas as pd
import pytest

spadl = pytest.importorskip("socceraction.spadl")

from skm.models.moments import build_moments  # noqa: E402
from skm.viz.replay import build_replay_data, render_html  # noqa: E402


def _type_id(name):
    types = spadl.actiontypes_df()
    return int(types.loc[types["type_name"] == name, "type_id"].iloc[0])


def _actions():
    rows = []
    for i, (team, tname) in enumerate([(10, "pass"), (10, "dribble"), (10, "shot"), (20, "pass")]):
        rows.append(
            {
                "game_id": 1,
                "period_id": 1,
                "time_seconds": float(i * 5),
                "team_id": team,
                "player_id": i + 1,
                "type_id": _type_id(tname),
                "result_id": 1,
                "bodypart_id": int(spadl.bodyparts_df()["bodypart_id"].iloc[0]),
                "action_id": i,
                "start_x": 50.0 + i,
                "start_y": 40.0,
                "end_x": 55.0 + i,
                "end_y": 40.0,
                "delta_p": 0.01,
                "skm": 0.01,
            }
        )
    return pd.DataFrame(rows)


def test_build_replay_data_and_render():
    actions = _actions()
    moments, _, _ = build_moments(actions, home_teams={1: 10})
    data = build_replay_data(1, actions, events=None)

    assert data["meta"]["game_id"] == 1
    assert len(data["actions"]) == 4
    assert len(data["moments"]) == len(moments)
    # action moment ids all resolve to a moment row (banner lookup)
    mids = {m["mid"] for m in data["moments"]}
    assert all(a["mid"] in mids for a in data["actions"])
    # goal flag: the successful shot
    assert any(a["goal"] for a in data["actions"])
    # home team listed first → shot action has team 0
    shot = [a for a in data["actions"] if a["type"] == "shot"][0]
    assert shot["team"] == 0

    html = render_html(data)
    assert "__SKM_REPLAY_DATA__" not in html
    # embedded payload round-trips
    start = html.index("const DATA = ") + len("const DATA = ")
    end = html.index(";\n", start)
    parsed = json.loads(html[start:end])
    assert parsed["meta"]["game_id"] == 1
    assert "not broadcast footage" in html
