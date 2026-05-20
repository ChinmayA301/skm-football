"""VAEP training with sklearn only (no xgboost/lightgbm/libomp)."""

from __future__ import annotations

import math
from typing import Dict

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier

from skm.models.booster_compat import stub_broken_boosters

stub_broken_boosters()

import socceraction.spadl as spadlcfg
from socceraction.vaep import features as vaep_fs
from socceraction.vaep import formula as vaep_formula
from socceraction.vaep import labels as vaep_lab
from socceraction.vaep.base import xfns_default

from skm.config import VAEP_MAX_DEPTH, VAEP_N_ESTIMATORS, VAEP_NB_PREV_ACTIONS


class SklearnVAEP:
    """Minimal VAEP API using sklearn GBM (works without OpenMP/libomp)."""

    def __init__(self, nb_prev_actions: int = VAEP_NB_PREV_ACTIONS) -> None:
        self.nb_prev_actions = nb_prev_actions
        self.xfns = list(xfns_default)
        self.yfns = [vaep_lab.scores, vaep_lab.concedes]
        self._models: Dict[str, GradientBoostingClassifier] = {}

    def compute_features(self, game: pd.Series, game_actions: pd.DataFrame) -> pd.DataFrame:
        named = spadlcfg.add_names(game_actions)
        states = vaep_fs.gamestates(named, self.nb_prev_actions)
        states = vaep_fs.play_left_to_right(states, game.home_team_id)
        return pd.concat([fn(states) for fn in self.xfns], axis=1)

    def compute_labels(self, game: pd.Series, game_actions: pd.DataFrame) -> pd.DataFrame:
        named = spadlcfg.add_names(game_actions)
        return pd.concat([fn(named) for fn in self.yfns], axis=1)

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.DataFrame,
        val_size: float = 0.2,
    ) -> "SklearnVAEP":
        cols = vaep_fs.feature_column_names(self.xfns, self.nb_prev_actions)
        n = len(X)
        idx = np.random.permutation(n)
        split = math.floor(n * (1 - val_size))
        train_idx = idx[:split]

        for col in y.columns:
            model = GradientBoostingClassifier(
                n_estimators=VAEP_N_ESTIMATORS,
                max_depth=VAEP_MAX_DEPTH,
                random_state=42,
            )
            model.fit(X.iloc[train_idx][cols], y.iloc[train_idx][col])
            self._models[col] = model
        return self

    def rate(self, game: pd.Series, game_actions: pd.DataFrame) -> pd.DataFrame:
        # groupby leaves non-contiguous index; formula.value requires aligned Series
        actions = game_actions.reset_index(drop=True)
        cols = vaep_fs.feature_column_names(self.xfns, self.nb_prev_actions)
        X = self.compute_features(game, actions)
        y_hat = pd.DataFrame(
            {col: self._models[col].predict_proba(X[cols])[:, 1] for col in self._models},
            index=actions.index,
        )
        named = spadlcfg.add_names(actions)
        return vaep_formula.value(named, y_hat.scores, y_hat.concedes)
