import pandas as pd
import pytest

from skm.models.match_context import (
    STAGE_WEIGHT,
    load_human_context,
    match_importance,
    team_strength,
)


def _games():
    # Two competitions. Comp A: team 1 strong (wins big), team 2 weak.
    return pd.DataFrame(
        {
            "game_id": [1, 2, 3, 4],
            "competition": ["A", "A", "B", "B"],
            "home_team_id": [1, 1, 5, 6],
            "away_team_id": [2, 2, 6, 5],
            "home_score": [3, 2, 1, 1],
            "away_score": [0, 0, 1, 0],
        }
    )


def test_team_strength_is_within_competition():
    ts = team_strength(_games()).set_index(["competition", "team_id"])["strength"]
    # In comp A, team 1 (won 3-0, 2-0) is stronger than team 2
    assert ts.loc[("A", 1)] > ts.loc[("A", 2)]
    # z-scored within competition → each competition centered near 0
    assert abs(ts.loc["A"].mean()) < 1e-9


def test_match_importance_up_vs_strong_opponent_and_knockout():
    games = _games()
    actions = pd.DataFrame(
        {"game_id": [1, 1], "team_id": [1, 2], "x": [0, 0]}
    )
    # game 1 as a Final vs Group game
    mi_final = match_importance(actions, games, stage_map={1: "Final"})
    mi_group = match_importance(actions, games, stage_map={1: "Group Stage"})
    assert (mi_final > mi_group).all()  # knockout weight applies
    # team 2 (facing strong team 1) gets a higher opponent-strength weight than
    # team 1 (facing weak team 2), at the same stage
    assert mi_group.iloc[1] > mi_group.iloc[0]


def test_stage_weights_ordered():
    assert STAGE_WEIGHT["Final"] > STAGE_WEIGHT["Semi-finals"] > STAGE_WEIGHT["Group Stage"]
    assert STAGE_WEIGHT["Regular Season"] == 1.0


def test_human_context_defaults_neutral(tmp_path):
    assert load_human_context(tmp_path / "missing.csv") == {}
    p = tmp_path / "hc.csv"
    p.write_text("game_id,importance_mult,note\n1,1.5,title decider\n")
    assert load_human_context(p) == {1: 1.5}
    # applied as a multiplier
    games = _games()
    actions = pd.DataFrame({"game_id": [1], "team_id": [1]})
    base = match_importance(actions, games, stage_map={1: "Group Stage"})
    boosted = match_importance(actions, games, stage_map={1: "Group Stage"}, human_context={1: 1.5})
    assert boosted.iloc[0] == pytest.approx(base.iloc[0] * 1.5)
