"""Train VAEP and compute ΔP (vaep_value) per SPADL action."""

from __future__ import annotations

import logging
import os
from typing import List, Optional, Tuple

import pandas as pd

from skm.config import VAEP_MAX_DEPTH, VAEP_N_ESTIMATORS, VAEP_NB_PREV_ACTIONS
from skm.models.booster_compat import stub_broken_boosters

logger = logging.getLogger(__name__)


def _collect_xy(
    games: pd.DataFrame,
    actions: pd.DataFrame,
    vaep_model,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    x_parts: List[pd.DataFrame] = []
    y_parts: List[pd.DataFrame] = []

    for game_id, game_actions in actions.groupby("game_id"):
        game = games.loc[game_id]
        x_parts.append(vaep_model.compute_features(game, game_actions))
        y_parts.append(vaep_model.compute_labels(game, game_actions))

    return pd.concat(x_parts, ignore_index=True), pd.concat(y_parts, ignore_index=True)


def _try_socceraction_vaep():
    stub_broken_boosters()
    try:
        from socceraction.vaep import VAEP

        return VAEP, "socceraction"
    except (ImportError, OSError):
        return None, None


def _booster_available(name: str) -> bool:
    try:
        mod = __import__(name)
    except (ImportError, OSError):
        return False
    return bool(getattr(mod, "__file__", None))


def _pick_learner() -> Optional[str]:
    for name in ("catboost", "xgboost", "lightgbm"):
        if _booster_available(name):
            return name
    return None


def train_vaep(
    games: pd.DataFrame,
    actions: pd.DataFrame,
    n_estimators: int = VAEP_N_ESTIMATORS,
    max_depth: int = VAEP_MAX_DEPTH,
) -> object:
    stub_broken_boosters()
    use_boosters = os.environ.get("SKM_VAEP_USE_BOOSTERS", "").lower() in ("1", "true", "yes")

    if use_boosters:
        VAEP_cls, kind = _try_socceraction_vaep()
        learner = _pick_learner() if VAEP_cls is not None else None
        if VAEP_cls is not None and learner is not None:
            vaep = VAEP_cls(nb_prev_actions=VAEP_NB_PREV_ACTIONS)
            X, y = _collect_xy(games, actions, vaep)
            logger.info("Training VAEP on %s states (%s via %s)", len(X), learner, kind)
            tree_params = (
                {
                    "n_estimators": n_estimators,
                    "max_depth": max_depth,
                    "eval_metric": "auc",
                    "early_stopping_rounds": 8,
                    "enable_categorical": True,
                }
                if learner == "xgboost"
                else {"n_estimators": n_estimators, "max_depth": max_depth}
            )
            vaep.fit(
                X,
                y,
                learner=learner,
                val_size=0.2,
                tree_params=tree_params,
                fit_params={"verbose": False},
            )
            return vaep

    from skm.models.vaep_sklearn import SklearnVAEP

    logger.info("Using sklearn GradientBoosting VAEP (no libomp / booster required)")
    vaep = SklearnVAEP(nb_prev_actions=VAEP_NB_PREV_ACTIONS)
    X, y = _collect_xy(games, actions, vaep)
    vaep.fit(X, y, val_size=0.2)
    return vaep


def rate_all_actions(
    games: pd.DataFrame,
    actions: pd.DataFrame,
    vaep_model,
) -> pd.DataFrame:
    rated_parts: List[pd.DataFrame] = []

    for game_id, game_actions in actions.groupby("game_id"):
        game = games.loc[game_id]
        ratings = vaep_model.rate(game, game_actions)
        out = game_actions.copy()
        out["delta_p"] = ratings["vaep_value"].to_numpy()
        out["offensive_value"] = ratings["offensive_value"].values
        out["defensive_value"] = ratings["defensive_value"].values
        rated_parts.append(out)

    return pd.concat(rated_parts, ignore_index=True)
