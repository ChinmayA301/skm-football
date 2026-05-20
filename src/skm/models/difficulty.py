"""Difficulty multiplier D from completion probability."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from skm.config import D_CLIP

ON_BALL_TYPES = {
    "pass",
    "cross",
    "dribble",
    "shot",
    "shot_penalty",
    "shot_freekick",
    "keeper_save",
}


def _action_features(actions: pd.DataFrame) -> pd.DataFrame:
    """Build features for completion / success probability."""
    df = actions.copy()
    df["dist"] = np.sqrt(
        (df["end_x"] - df["start_x"]) ** 2 + (df["end_y"] - df["start_y"]) ** 2
    ).fillna(0)
    df["success"] = (df["result_name"] == "success").astype(int)
    df["under_pressure"] = df.get("under_pressure", False).fillna(False).astype(int)
    return df


def fit_difficulty_model(actions: pd.DataFrame) -> tuple:
    """Train logistic model; return (model, scaler, feature_cols)."""
    import socceraction.spadl as spadl

    named = spadl.add_names(actions)
    train = named[named["type_name"].isin(ON_BALL_TYPES)].copy()
    train = train[train["type_name"].isin(["pass", "cross", "dribble"])]

    if len(train) < 500:
        train = named[named["type_name"].isin(ON_BALL_TYPES)].copy()

    train = _action_features(train)
    feature_cols = ["start_x", "start_y", "end_x", "end_y", "dist", "under_pressure"]
    X = train[feature_cols].fillna(0)
    y = train["success"]

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    model = LogisticRegression(max_iter=500, class_weight="balanced")
    model.fit(Xs, y)
    return model, scaler, feature_cols


def compute_difficulty(
    actions: pd.DataFrame,
    model=None,
    scaler=None,
    feature_cols=None,
) -> pd.Series:
    """D_i = 1 / P(success), clipped to D_CLIP."""
    if model is None:
        model, scaler, feature_cols = fit_difficulty_model(actions)

    import socceraction.spadl as spadl

    named = spadl.add_names(actions)
    df = _action_features(named)
    X = df[feature_cols].fillna(0)
    Xs = scaler.transform(X)

    p_success = model.predict_proba(Xs)[:, 1]
    p_success = np.clip(p_success, 0.05, 0.95)
    d = 1.0 / p_success
    d = np.clip(d, D_CLIP[0], D_CLIP[1])
    return pd.Series(d, index=actions.index)
