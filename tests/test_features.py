from skm.data.features import (
    assign_zone,
    is_progressive,
    minute_bucket,
    scoreline_state,
)


def test_assign_zone_center():
    assert assign_zone(60.0, 40.0) == "6_4"


def test_progressive_pass_forward():
    assert is_progressive(50.0, 40.0, 65.0, 40.0, attacking_right=True) is True


def test_minute_bucket():
    assert minute_bucket(78) == "75-90"


def test_scoreline_state():
    assert scoreline_state(1, 1, team_is_home=True) == "drawing"
    assert scoreline_state(2, 1, team_is_home=False) == "trailing"
