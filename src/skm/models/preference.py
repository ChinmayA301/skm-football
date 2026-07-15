"""Expert-preference calibration of moment values (Bradley-Terry).

The honest path to "training on expert takes": collect pairwise judgments
over *moments* ("which of these two moments mattered more?") and learn a
re-weighting of moment features that agrees with them. Pairwise moment
preferences avoid the outcome bias of match ratings — the very bias SKM
exists to correct — because the expert compares situations, not stat lines.

This is preference-based reward learning (the supervised core of RLHF).
A full RL loop (policy proposes weightings, expert feedback updates a
reward model) can sit on top later; the learner below is the reward model.

No expert labels ship with this repo. `data/external/expert_moment_labels.csv`
is a header-only template; fill it from your own annotation sessions
(dashboard moment map + replay make good labeling surfaces).

Label schema (one row per comparison):
    game_id_a, moment_id_a, game_id_b, moment_id_b, preferred (a|b),
    annotator, note
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

DEFAULT_FEATURES = [
    "skm_sum",
    "delta_p_sum",
    "n_actions",
    "contains_shot",
    "is_transition",
    "is_set_piece",
]


def moment_features(moments: pd.DataFrame) -> pd.DataFrame:
    """Feature frame for preference learning, indexed like `moments`."""
    f = pd.DataFrame(index=moments.index)
    f["skm_sum"] = moments["skm_sum"].fillna(0)
    f["delta_p_sum"] = moments["delta_p_sum"].fillna(0)
    f["n_actions"] = moments["n_actions"].fillna(0)
    f["contains_shot"] = moments["contains_shot"].astype(float)
    f["is_transition"] = (moments["moment_type"] == "transition").astype(float)
    f["is_set_piece"] = (moments["moment_type"] == "set_piece").astype(float)
    return f


def fit_preference_model(
    moments: pd.DataFrame,
    pairs: pd.DataFrame,
    feature_cols: Optional[List[str]] = None,
) -> Dict:
    """
    Bradley-Terry: P(a preferred over b) = sigmoid(w · (f_a − f_b)).

    `moments` must carry (game_id, moment_id); `pairs` references them via
    *_a / *_b columns plus `preferred` in {"a", "b"}.
    Returns {"weights": Series, "feature_cols": [...], "n_pairs": int}.
    """
    from sklearn.linear_model import LogisticRegression

    feature_cols = feature_cols or DEFAULT_FEATURES
    feats = moment_features(moments)
    # Standardize so regularization doesn't favor large-scale features
    scale = feats.std().replace(0, 1.0)
    feats = feats / scale
    key = moments.set_index(["game_id", "moment_id"]).index
    lookup = pd.DataFrame(feats.values, index=key, columns=feature_cols)

    diffs, ys = [], []
    for _, p in pairs.iterrows():
        ka = (p["game_id_a"], p["moment_id_a"])
        kb = (p["game_id_b"], p["moment_id_b"])
        if ka not in lookup.index or kb not in lookup.index:
            continue
        diffs.append(lookup.loc[ka].to_numpy() - lookup.loc[kb].to_numpy())
        ys.append(1 if str(p["preferred"]).strip().lower() == "a" else 0)

    if len(ys) < 10:
        raise ValueError(f"Need ≥10 usable pairs, got {len(ys)} — collect more labels first.")

    X, y = np.vstack(diffs), np.array(ys)
    model = LogisticRegression(fit_intercept=False, max_iter=1000, C=1.0)
    model.fit(X, y)
    weights = pd.Series(model.coef_[0], index=feature_cols)
    acc = float(model.score(X, y))
    logger.info("Preference model: %s pairs, train accuracy %.2f", len(ys), acc)
    return {
        "weights": weights,
        "scale": scale,
        "feature_cols": feature_cols,
        "n_pairs": len(ys),
        "train_acc": acc,
    }


def score_moments(moments: pd.DataFrame, model: Dict) -> pd.Series:
    """Expert-calibrated moment score: w · standardized features (relative scale)."""
    feats = moment_features(moments)[model["feature_cols"]] / model["scale"]
    return pd.Series(feats.to_numpy() @ model["weights"].to_numpy(), index=moments.index)
