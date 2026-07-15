import numpy as np
import pandas as pd
import pytest

from skm.models.preference import fit_preference_model, score_moments


def _moments(n=40, seed=7):
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "game_id": 1,
            "moment_id": range(n),
            "skm_sum": rng.normal(0.05, 0.05, n),
            "delta_p_sum": rng.normal(0.04, 0.04, n),
            "n_actions": rng.integers(1, 12, n),
            "contains_shot": rng.random(n) > 0.7,
            "moment_type": rng.choice(["open_play", "transition", "set_piece"], n),
        }
    )


def _pairs_from_truth(moments, true_score, n_pairs=120, seed=3):
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n_pairs):
        a, b = rng.choice(len(moments), 2, replace=False)
        rows.append(
            {
                "game_id_a": 1,
                "moment_id_a": int(moments["moment_id"].iloc[a]),
                "game_id_b": 1,
                "moment_id_b": int(moments["moment_id"].iloc[b]),
                "preferred": "a" if true_score.iloc[a] > true_score.iloc[b] else "b",
            }
        )
    return pd.DataFrame(rows)


def test_recovers_ground_truth_ordering():
    moments = _moments()
    # Expert who values SKM plus a shot bonus
    truth = 2.0 * moments["skm_sum"] + 0.1 * moments["contains_shot"].astype(float)
    pairs = _pairs_from_truth(moments, truth)

    model = fit_preference_model(moments, pairs)
    assert model["n_pairs"] == len(pairs)
    assert model["weights"]["skm_sum"] > 0  # dominant signal recovered
    assert model["train_acc"] > 0.85

    scores = score_moments(moments, model)
    rho = scores.corr(truth, method="spearman")
    assert rho > 0.9  # learned ordering matches the expert's


def test_too_few_pairs_raises():
    moments = _moments(n=6)
    truth = moments["skm_sum"]
    pairs = _pairs_from_truth(moments, truth, n_pairs=4)
    with pytest.raises(ValueError, match="pairs"):
        fit_preference_model(moments, pairs)
