"""Pitch-coordinate tracks → pressure geometry → 360-agreement gate.

Everything here is pure math over DataFrames — no video or model
dependencies — so the whole module is unit-testable without a clip.

Input track schema (one row per detection, pitch coordinates in meters,
SPADL frame: x ∈ [0, 120], y ∈ [0, 80]):

    frame, t_video, track_id, cls ("person" | "ball"), x, y, conf, r, g, b

The gate: CV-derived nearest-defender distances at event times must agree
with StatsBomb 360 freeze-frame values (Spearman ρ and MAE) before any
CV-derived number is used downstream. Thresholds are provisional and
disclosed, not tuned.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Provisional gate thresholds (documented in docs/CV_PILOT.md)
GATE_MIN_RHO = 0.5
GATE_MAX_MAE_M = 3.0
GATE_MIN_EVENTS = 10

CARRIER_MAX_DIST_M = 3.0  # ball within this of a player → that player carries
PAIR_TOLERANCE_S = 0.5  # max |t_event − t_frame| when pairing with 360


def assign_teams(tracks: pd.DataFrame, n_clusters: int = 2) -> Dict[int, int]:
    """
    track_id → team {0, 1} from jersey color (median RGB per track).

    2-means on shirt color is the honest pilot baseline. Known limits:
    referees and goalkeepers can land in either cluster; check the split
    visually before trusting it. Track-level medians resist per-frame
    lighting noise.
    """
    from sklearn.cluster import KMeans

    persons = tracks[tracks["cls"] == "person"]
    colors = persons.groupby("track_id")[["r", "g", "b"]].median()
    if len(colors) < n_clusters:
        raise ValueError(f"Need ≥{n_clusters} person tracks, got {len(colors)}")

    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = km.fit_predict(colors.values)
    return {int(tid): int(lab) for tid, lab in zip(colors.index, labels)}


def _carrier(players: pd.DataFrame, ball_x: float, ball_y: float) -> Optional[pd.Series]:
    d = np.sqrt((players["x"] - ball_x) ** 2 + (players["y"] - ball_y) ** 2)
    if d.min() > CARRIER_MAX_DIST_M:
        return None
    return players.loc[d.idxmin()]


def pressure_timeline(tracks: pd.DataFrame, teams: Dict[int, int]) -> pd.DataFrame:
    """
    Per-frame pressure geometry around the ball carrier.

    Frames without a ball detection, or where no player is within
    CARRIER_MAX_DIST_M of the ball, produce no row — coverage is reported
    by the caller, never silently interpolated.

    Returns: t_video, frame, carrier_track, carrier_team,
             nearest_def_m, n_def_5m, n_def_10m, n_players_visible
    """
    df = tracks.copy()
    df["team"] = df["track_id"].map(teams)

    rows = []
    for frame, grp in df.groupby("frame"):
        ball = grp[grp["cls"] == "ball"]
        players = grp[(grp["cls"] == "person") & grp["team"].notna()]
        if ball.empty or len(players) < 2:
            continue
        bx, by = float(ball["x"].iloc[0]), float(ball["y"].iloc[0])
        carrier = _carrier(players, bx, by)
        if carrier is None:
            continue
        opponents = players[players["team"] != carrier["team"]]
        if opponents.empty:
            continue
        d = np.sqrt((opponents["x"] - carrier["x"]) ** 2 + (opponents["y"] - carrier["y"]) ** 2)
        rows.append(
            {
                "frame": int(frame),
                "t_video": float(grp["t_video"].iloc[0]),
                "carrier_track": int(carrier["track_id"]),
                "carrier_team": int(carrier["team"]),
                "nearest_def_m": float(d.min()),
                "n_def_5m": int((d <= 5.0).sum()),
                "n_def_10m": int((d <= 10.0).sum()),
                "n_players_visible": len(players),
            }
        )
    return pd.DataFrame(rows)


def agreement_report(
    pressure: pd.DataFrame,
    actions: pd.DataFrame,
    game_id: int,
    period_id: int,
    offset_s: float,
) -> dict:
    """
    The gate: pair CV pressure with StatsBomb 360 features at event times.

    `offset_s` is the match clock (period time_seconds) at t_video = 0.
    Events of `game_id`/`period_id` falling inside the clip window are
    paired with the nearest CV frame within PAIR_TOLERANCE_S.

    Returns a dict with the paired frame, Spearman ρ, MAE, coverage, and
    a pass/fail verdict against the provisional thresholds.
    """
    if pressure.empty:
        return {"n_pairs": 0, "passed": False, "reason": "no CV pressure frames"}

    ev = actions[
        (actions["game_id"] == game_id)
        & (actions["period_id"] == period_id)
        & actions["nearest_def_m"].notna()
    ].copy()
    if ev.empty:
        return {"n_pairs": 0, "passed": False, "reason": "no 360-covered events for this game/period"}

    t0, t1 = offset_s, offset_s + pressure["t_video"].max()
    ev = ev[ev["time_seconds"].between(t0, t1)]
    if ev.empty:
        return {"n_pairs": 0, "passed": False, "reason": "no events inside the clip window"}

    cv_t = pressure["t_video"].to_numpy() + offset_s
    pairs = []
    for _, e in ev.iterrows():
        i = int(np.argmin(np.abs(cv_t - e["time_seconds"])))
        if abs(cv_t[i] - e["time_seconds"]) > PAIR_TOLERANCE_S:
            continue
        pairs.append(
            {
                "time_seconds": float(e["time_seconds"]),
                "cv_nearest_def_m": float(pressure["nearest_def_m"].iloc[i]),
                "sb_nearest_def_m": float(e["nearest_def_m"]),
                "cv_n_def_5m": int(pressure["n_def_5m"].iloc[i]),
                "sb_n_def_5m": int(e["n_def_5m"]),
            }
        )
    paired = pd.DataFrame(pairs)
    if len(paired) < GATE_MIN_EVENTS:
        return {
            "n_pairs": len(paired),
            "paired": paired,
            "passed": False,
            "reason": f"only {len(paired)} paired events (< {GATE_MIN_EVENTS}) — use a longer clip",
        }

    rho = float(paired["cv_nearest_def_m"].corr(paired["sb_nearest_def_m"], method="spearman"))
    mae = float((paired["cv_nearest_def_m"] - paired["sb_nearest_def_m"]).abs().mean())
    passed = rho >= GATE_MIN_RHO and mae <= GATE_MAX_MAE_M
    return {
        "n_pairs": len(paired),
        "paired": paired,
        "rho": rho,
        "mae_m": mae,
        "thresholds": {"min_rho": GATE_MIN_RHO, "max_mae_m": GATE_MAX_MAE_M},
        "passed": passed,
        "reason": "gate passed" if passed else "CV geometry disagrees with 360 ground truth",
    }
