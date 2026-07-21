import json

import numpy as np
import pandas as pd
import pytest

from skm.video.calibration import (
    apply_homography,
    fit_homography,
    load_calibration,
    reprojection_error,
)
from skm.video.geometry import (
    agreement_report,
    assign_teams,
    pressure_timeline,
)

# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------


def _perspective_pairs(n=6, seed=1):
    """Ground-truth projective camera: pitch → pixels via a known H."""
    rng = np.random.default_rng(seed)
    H_true = np.array([[8.0, 1.2, 300.0], [0.4, -9.5, 900.0], [0.001, 0.004, 1.0]])
    pitch = np.column_stack(
        [rng.uniform(0, 120, n), rng.uniform(0, 80, n)]
    )
    homog = np.column_stack([pitch, np.ones(n)])
    px = (np.linalg.inv(H_true) @ homog.T).T
    px = px[:, :2] / px[:, 2:3]
    return px, pitch


def test_homography_recovers_projective_mapping():
    px, pitch = _perspective_pairs()
    H = fit_homography(px, pitch)
    assert reprojection_error(H, px, pitch) < 1e-6
    # unseen point maps correctly
    px2, pitch2 = _perspective_pairs(n=3, seed=7)
    assert np.allclose(apply_homography(H, px2), pitch2, atol=1e-5)


def test_homography_needs_four_points():
    with pytest.raises(ValueError, match="at least 4"):
        fit_homography(np.zeros((3, 2)), np.zeros((3, 2)))


def test_load_calibration_rejects_bad_landmarks(tmp_path):
    # Degenerate/inconsistent points → high reprojection error → rejected
    bad = {
        "points": [
            {"px": 0, "py": 0, "x": 0, "y": 0},
            {"px": 100, "py": 0, "x": 120, "y": 0},
            {"px": 0, "py": 100, "x": 0, "y": 80},
            {"px": 100, "py": 100, "x": 120, "y": 80},
            {"px": 50, "py": 50, "x": 0, "y": 0},  # contradicts the first point
        ]
    }
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="reprojection"):
        load_calibration(p)


def test_load_calibration_roundtrip(tmp_path):
    px, pitch = _perspective_pairs()
    good = {
        "points": [
            {"px": float(a), "py": float(b), "x": float(c), "y": float(d)}
            for (a, b), (c, d) in zip(px, pitch)
        ]
    }
    p = tmp_path / "good.json"
    p.write_text(json.dumps(good))
    H = load_calibration(p)
    assert reprojection_error(H, px, pitch) < 1e-6


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------


def _tracks(rows):
    defaults = {"conf": 0.9, "r": 128.0, "g": 128.0, "b": 128.0, "t_video": 0.0}
    return pd.DataFrame([{**defaults, **r} for r in rows])


def test_assign_teams_splits_by_shirt_color():
    rows = []
    for tid in range(1, 6):  # reds
        rows.append({"frame": 0, "track_id": tid, "cls": "person", "x": 10, "y": 10,
                     "r": 210.0 + tid, "g": 30.0, "b": 30.0})
    for tid in range(6, 11):  # blues
        rows.append({"frame": 0, "track_id": tid, "cls": "person", "x": 20, "y": 20,
                     "r": 30.0, "g": 30.0, "b": 200.0 + tid})
    teams = assign_teams(_tracks(rows))
    reds = {teams[t] for t in range(1, 6)}
    blues = {teams[t] for t in range(6, 11)}
    assert len(reds) == 1 and len(blues) == 1 and reds != blues


def test_pressure_timeline_geometry():
    teams = {1: 0, 2: 1, 3: 1}
    rows = [
        {"frame": 0, "t_video": 0.0, "track_id": 1, "cls": "person", "x": 60.0, "y": 40.0},
        {"frame": 0, "t_video": 0.0, "track_id": 2, "cls": "person", "x": 64.0, "y": 40.0},
        {"frame": 0, "t_video": 0.0, "track_id": 3, "cls": "person", "x": 60.0, "y": 48.0},
        {"frame": 0, "t_video": 0.0, "track_id": -1, "cls": "ball", "x": 61.0, "y": 40.0},
    ]
    p = pressure_timeline(_tracks(rows), teams)
    assert len(p) == 1
    row = p.iloc[0]
    assert row["carrier_track"] == 1  # nearest to ball, within 3 m
    assert row["nearest_def_m"] == pytest.approx(4.0)  # track 2
    assert row["n_def_5m"] == 1
    assert row["n_def_10m"] == 2


def test_pressure_timeline_skips_ballless_and_distant_frames():
    teams = {1: 0, 2: 1}
    rows = [
        # frame 0: no ball
        {"frame": 0, "t_video": 0.0, "track_id": 1, "cls": "person", "x": 60, "y": 40},
        {"frame": 0, "t_video": 0.0, "track_id": 2, "cls": "person", "x": 65, "y": 40},
        # frame 1: ball 20 m from everyone → no carrier
        {"frame": 1, "t_video": 0.04, "track_id": 1, "cls": "person", "x": 60, "y": 40},
        {"frame": 1, "t_video": 0.04, "track_id": 2, "cls": "person", "x": 65, "y": 40},
        {"frame": 1, "t_video": 0.04, "track_id": -1, "cls": "ball", "x": 60, "y": 60},
    ]
    assert pressure_timeline(_tracks(rows), teams).empty


# ---------------------------------------------------------------------------
# Agreement gate
# ---------------------------------------------------------------------------


def _gate_fixtures(n=20, noise=0.3, seed=5):
    rng = np.random.default_rng(seed)
    t_events = np.sort(rng.uniform(0, 60, n))
    sb = rng.uniform(1, 12, n)  # 360 ground truth nearest-defender distances
    pressure = pd.DataFrame(
        {
            "frame": range(n),
            "t_video": t_events,  # offset 0 → aligned
            "carrier_track": 1,
            "carrier_team": 0,
            "nearest_def_m": sb + rng.normal(0, noise, n),
            "n_def_5m": (sb <= 5).astype(int),
            "n_def_10m": (sb <= 10).astype(int),
            "n_players_visible": 10,
        }
    )
    actions = pd.DataFrame(
        {
            "game_id": 1,
            "period_id": 1,
            "time_seconds": t_events,
            "nearest_def_m": sb,
            "n_def_5m": (sb <= 5).astype(int),
        }
    )
    return pressure, actions


def test_agreement_gate_passes_on_consistent_geometry():
    pressure, actions = _gate_fixtures(noise=0.3)
    rep = agreement_report(pressure, actions, game_id=1, period_id=1, offset_s=0.0)
    assert rep["n_pairs"] == 20
    assert rep["passed"] is True
    assert rep["rho"] > 0.9
    assert rep["mae_m"] < 1.0


def test_agreement_gate_fails_on_garbage_geometry():
    pressure, actions = _gate_fixtures()
    pressure["nearest_def_m"] = np.random.default_rng(0).uniform(1, 12, len(pressure))
    rep = agreement_report(pressure, actions, game_id=1, period_id=1, offset_s=0.0)
    assert rep["passed"] is False


def test_agreement_gate_requires_events_in_window():
    pressure, actions = _gate_fixtures()
    rep = agreement_report(pressure, actions, game_id=1, period_id=1, offset_s=5000.0)
    assert rep["n_pairs"] == 0
    assert rep["passed"] is False


def test_agreement_gate_needs_min_pairs():
    pressure, actions = _gate_fixtures(n=4)
    rep = agreement_report(pressure, actions, game_id=1, period_id=1, offset_s=0.0)
    assert rep["passed"] is False
    assert "paired events" in rep["reason"]
