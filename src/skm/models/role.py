"""Role factor R from player archetypes and action unusualness."""

from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from skm.config import R_CLIP, ROLE_N_CLUSTERS

# SPADL type_name buckets for player profiles
PROFILE_TYPES = [
    "pass",
    "cross",
    "dribble",
    "shot",
    "interception",
    "tackle",
    "clearance",
    "keeper_save",
]


def _player_action_rates(actions: pd.DataFrame) -> pd.DataFrame:
    import socceraction.spadl as spadl

    named = spadl.add_names(actions)
    named = named[named["player_id"].notna()].copy()
    named["player_id"] = named["player_id"].astype(int)

    counts = (
        named.groupby(["player_id", "type_name"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=PROFILE_TYPES, fill_value=0)
    )
    totals = counts.sum(axis=1).replace(0, 1)
    rates = counts.div(totals, axis=0)
    rates.columns = [f"rate_{c}" for c in rates.columns]
    return rates


def fit_role_clusters(actions: pd.DataFrame, n_clusters: int = ROLE_N_CLUSTERS) -> Dict:
    rates = _player_action_rates(actions)
    scaler = StandardScaler()
    X = scaler.fit_transform(rates.values)
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = km.fit_predict(X)

    rates["cluster"] = labels
    cluster_profiles = rates.groupby("cluster")[rates.columns.difference(["cluster"])].mean()

    return {
        "scaler": scaler,
        "kmeans": km,
        "rates": rates,
        "cluster_profiles": cluster_profiles,
        "feature_cols": list(rates.columns.difference(["cluster"])),
    }


def compute_role(actions: pd.DataFrame, role_state: Dict) -> pd.Series:
    """
  R_i > 1 when action type is unusually valuable for this player's role cluster.
    """
    import socceraction.spadl as spadl

    named = spadl.add_names(actions)
    rates = role_state["rates"]
    cluster_profiles = role_state["cluster_profiles"]

    player_cluster = rates["cluster"].to_dict()
    r_values = np.ones(len(named))

    for i, (_, row) in enumerate(named.iterrows()):
        pid = row.get("player_id")
        if pd.isna(pid):
            continue
        pid = int(pid)
        if pid not in player_cluster:
            continue
        cluster = player_cluster[pid]
        action_type = row["type_name"]
        col = f"rate_{action_type}"
        if col not in cluster_profiles.columns:
            continue
        cluster_mean = float(cluster_profiles.loc[cluster, col])
        player_rate = float(rates.loc[pid, col]) if pid in rates.index else cluster_mean
        if cluster_mean > 0.01:
            ratio = player_rate / cluster_mean
            r_values[i] = np.clip(1.0 / max(ratio, 0.1), R_CLIP[0], R_CLIP[1])
        else:
            r_values[i] = 1.1

    return pd.Series(r_values, index=actions.index)
