import pandas as pd
import pytest

spadl = pytest.importorskip("socceraction.spadl")

from skm.models.competence import competence_scores  # noqa: E402


def _type_id(name):
    t = spadl.actiontypes_df()
    return int(t.loc[t["type_name"] == name, "type_id"].iloc[0])


def _actions(rows):
    bp = int(spadl.bodyparts_df()["bodypart_id"].iloc[0])
    res = int(spadl.results_df().iloc[0]["result_id"])
    out = []
    for i, r in enumerate(rows):
        out.append(
            {
                "game_id": 1,
                "period_id": 1,
                "time_seconds": float(i),
                "action_id": i,
                "team_id": 10,
                "bodypart_id": bp,
                "result_id": res,
                "start_x": 50.0,
                "start_y": 40.0,
                "end_x": 55.0,
                "end_y": 40.0,
                **r,
            }
        )
    return pd.DataFrame(out)


def test_competence_rewards_above_positional_peer():
    """A DM whose tackles are above the DM-tackle baseline scores positive;
    one below scores negative — measured within position, not vs attackers."""
    tackle = _type_id("tackle")
    rows = []
    # 40 DM tackles from peers at skm ~0.01 (baseline)
    for p in range(2, 12):
        for _ in range(4):
            rows.append({"player_id": p, "position_group": "DM", "type_id": tackle, "skm": 0.01})
    # player 1: DM, tackles well above baseline
    for _ in range(30):
        rows.append({"player_id": 1, "position_group": "DM", "type_id": tackle, "skm": 0.05})
    # player 99: DM, tackles below baseline
    for _ in range(30):
        rows.append({"player_id": 99, "position_group": "DM", "type_id": tackle, "skm": -0.02})
    board = competence_scores(_actions(rows), min_actions=20)
    c = board.set_index("player_id")["competence"]
    assert c.loc[1] > 0
    assert c.loc[99] < 0
    assert c.loc[1] > c.loc[99]


def test_competence_is_position_relative_not_absolute_value():
    """A striker with high-value shots and a DM with modest-but-elite tackles
    can both score well — value is judged within position, so the DM is not
    buried just because shots carry more raw value."""
    shot = _type_id("shot")
    tackle = _type_id("tackle")
    rows = []
    # striker peers: shots ~0.1
    for p in range(20, 30):
        for _ in range(5):
            rows.append({"player_id": p, "position_group": "ST", "type_id": shot, "skm": 0.10})
    # DM peers: tackles ~0.01
    for p in range(30, 40):
        for _ in range(5):
            rows.append({"player_id": p, "position_group": "DM", "type_id": tackle, "skm": 0.01})
    # elite DM: tackles well above DM peers (but tiny absolute value)
    for _ in range(40):
        rows.append({"player_id": 1, "position_group": "DM", "type_id": tackle, "skm": 0.03})
    # average striker: shots exactly at striker baseline
    for _ in range(40):
        rows.append({"player_id": 2, "position_group": "ST", "type_id": shot, "skm": 0.10})
    board = competence_scores(_actions(rows), min_actions=20)
    c = board.set_index("player_id")["competence"]
    # elite DM (tiny absolute value) beats the average striker (huge absolute value)
    assert c.loc[1] > c.loc[2]
    assert abs(c.loc[2]) < 1e-6  # exactly baseline → ~0 competence


def test_shrinkage_dampens_small_samples():
    tackle = _type_id("tackle")
    rows = []
    for p in range(2, 12):
        for _ in range(10):
            rows.append({"player_id": p, "position_group": "DM", "type_id": tackle, "skm": 0.01})
    # player A: 2 great tackles (small n) ; player B: 40 great tackles (large n)
    for _ in range(2):
        rows.append({"player_id": 1, "position_group": "DM", "type_id": tackle, "skm": 0.09})
    for _ in range(40):
        rows.append({"player_id": 2, "position_group": "DM", "type_id": tackle, "skm": 0.09})
    board = competence_scores(_actions(rows), min_actions=2)
    c = board.set_index("player_id")["competence"]
    # same per-action quality, but B's larger sample earns more credit
    assert c.loc[2] > c.loc[1]
