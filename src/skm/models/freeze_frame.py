"""Layer 3 (partial): pressure geometry from StatsBomb 360 freeze frames.

StatsBomb 360 provides player positions visible in the broadcast frame at
each event — real "video intelligence", already extracted and licensed.
Open data covers World Cup 2022 and Euro 2024 in our sample (~115 matches).

For each event with a freeze frame we compute:

- nearest_def_m: distance from the actor to the closest opponent
- n_def_5m / n_def_10m: opponents within 5 / 10 meters
- n_def_ahead: opponents between the actor and the goal (x > actor_x —
  StatsBomb event coordinates always attack left→right for the acting team)
- n_visible: players in frame (disclosure: frames only cover the camera view)

Then D_360 refits the completion-probability model with these features on
the covered subset, and skm_360 recombines SKM with D_360 where available
(falling back to event-only D elsewhere).

Usage:
    skm-build-360 --max-games 8   # prototype
    skm-build-360                 # all 360-covered matches
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

from skm.config import (
    ACTIONS_360_PARQUET,
    ACTIONS_SCORED_PARQUET,
    PRESSURE_RADIUS_TIGHT_M,
    PRESSURE_RADIUS_WIDE_M,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

FRAME_FEATURES = ["nearest_def_m", "n_def_5m", "n_def_10m", "n_def_ahead", "n_visible"]


def frame_features_for_match(game_id: int) -> Optional[pd.DataFrame]:
    """Per-event pressure geometry from 360 frames; None if unavailable."""
    from statsbombpy import sb

    try:
        frames = sb.frames(match_id=int(game_id), fmt="dataframe")
    except Exception as exc:
        logger.info("No 360 for game %s (%s)", game_id, str(exc)[:60])
        return None
    if frames is None or len(frames) == 0:
        return None

    loc = pd.DataFrame(frames["location"].tolist(), columns=["fx", "fy"], index=frames.index)
    frames = pd.concat([frames[["id", "teammate", "actor"]], loc], axis=1)
    return compute_frame_features(frames)


def compute_frame_features(frames: pd.DataFrame) -> pd.DataFrame:
    """Pure geometry: frames columns = id, teammate, actor, fx, fy."""
    rows: List[dict] = []
    for event_id, grp in frames.groupby("id"):
        actor = grp[grp["actor"] == True]  # noqa: E712
        if actor.empty:
            continue
        ax, ay = float(actor["fx"].iloc[0]), float(actor["fy"].iloc[0])
        opp = grp[(grp["teammate"] == False) & (grp["actor"] == False)]  # noqa: E712
        if opp.empty:
            rows.append(
                {
                    "original_event_id": event_id,
                    "nearest_def_m": 30.0,
                    "n_def_5m": 0,
                    "n_def_10m": 0,
                    "n_def_ahead": 0,
                    "n_visible": len(grp),
                }
            )
            continue
        d = np.sqrt((opp["fx"] - ax) ** 2 + (opp["fy"] - ay) ** 2)
        rows.append(
            {
                "original_event_id": event_id,
                "nearest_def_m": float(d.min()),
                "n_def_5m": int((d <= PRESSURE_RADIUS_TIGHT_M).sum()),
                "n_def_10m": int((d <= PRESSURE_RADIUS_WIDE_M).sum()),
                "n_def_ahead": int((opp["fx"] > ax).sum()),
                "n_visible": len(grp),
            }
        )
    return pd.DataFrame(rows)


def attach_frame_features(actions: pd.DataFrame, max_games: Optional[int] = None) -> pd.DataFrame:
    """Merge 360 features onto scored actions (NaN where not covered)."""
    out = actions.copy()
    game_ids = list(out["game_id"].unique())
    if max_games is not None:
        game_ids = game_ids[:max_games]

    parts = []
    covered = 0
    for gid in game_ids:
        ff = frame_features_for_match(int(gid))
        if ff is not None and len(ff):
            parts.append(ff)
            covered += 1
    logger.info("360 coverage: %s/%s games", covered, len(game_ids))
    if not parts:
        for col in FRAME_FEATURES:
            out[col] = np.nan
        return out

    feats = pd.concat(parts, ignore_index=True).drop_duplicates("original_event_id")
    return out.merge(feats, on="original_event_id", how="left")


def fit_difficulty_360(actions: pd.DataFrame) -> pd.Series:
    """Refit completion difficulty with pressure geometry on covered rows.

    Returns D_360 aligned to actions: geometry-aware where frames exist,
    otherwise the existing event-only D.
    """
    import socceraction.spadl as spadl
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    from skm.config import D_CLIP
    from skm.models.difficulty import ON_BALL_TYPES

    named = spadl.add_names(actions)
    named["dist"] = np.sqrt(
        (named["end_x"] - named["start_x"]) ** 2 + (named["end_y"] - named["start_y"]) ** 2
    ).fillna(0)
    named["success"] = (named["result_name"] == "success").astype(int)
    named["under_pressure_i"] = named.get("under_pressure", False).fillna(False).astype(int)

    feature_cols = [
        "start_x",
        "start_y",
        "end_x",
        "end_y",
        "dist",
        "under_pressure_i",
        "nearest_def_m",
        "n_def_5m",
        "n_def_10m",
        "n_def_ahead",
    ]
    covered = named["nearest_def_m"].notna() & named["type_name"].isin(ON_BALL_TYPES)
    train = named[covered].copy()
    if len(train) < 500:
        logger.warning("Too few 360-covered on-ball actions (%s); keeping event-only D", len(train))
        return actions["D"]

    X = train[feature_cols].fillna(0)
    scaler = StandardScaler()
    model = LogisticRegression(max_iter=500, class_weight="balanced")
    model.fit(scaler.fit_transform(X), train["success"])

    d360 = actions["D"].copy()
    Xall = named.loc[covered, feature_cols].fillna(0)
    p = np.clip(model.predict_proba(scaler.transform(Xall))[:, 1], 0.05, 0.95)
    d360.loc[covered[covered].index] = np.clip(1.0 / p, D_CLIP[0], D_CLIP[1])
    logger.info(
        "D_360 fitted on %s covered on-ball actions; coef(nearest_def_m)=%.3f",
        len(train),
        model.coef_[0][feature_cols.index("nearest_def_m")],
    )
    return d360


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Attach 360 pressure geometry and refit D")
    parser.add_argument("--actions-input", default=str(ACTIONS_SCORED_PARQUET))
    parser.add_argument("--output", default=str(ACTIONS_360_PARQUET))
    parser.add_argument("--max-games", type=int, default=None)
    args = parser.parse_args(argv)

    from skm.models.skm_combine import combine_skm

    actions = pd.read_parquet(args.actions_input)
    actions = attach_frame_features(actions, max_games=args.max_games)

    covered = actions["nearest_def_m"].notna()
    actions["D_360"] = fit_difficulty_360(actions).values
    actions["skm_360"] = combine_skm(actions, d_col="D_360").values

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    actions.to_parquet(out, index=False)
    logger.info("Wrote %s rows → %s", len(actions), out)

    sub = actions[covered]
    if len(sub):
        print(f"\n360-covered actions: {covered.sum():,} ({covered.mean():.1%} of sample)")
        print(f"corr(D, D_360) on covered rows: {sub['D'].corr(sub['D_360']):.3f}")
        print(f"corr(skm, skm_360): {sub['skm'].corr(sub['skm_360']):.3f}")
        moved = (sub["D_360"] - sub["D"]).abs()
        print(f"share of covered actions with |D_360 − D| > 0.5: {(moved > 0.5).mean():.1%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
