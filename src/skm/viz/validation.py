"""Validation: SKM vs internal metrics, outcomes, and external benchmarks."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

from skm.config import PROJECT_ROOT
from skm.viz.loaders import enrich_leaderboard, load_events, load_leaderboard

EXTERNAL_BENCHMARKS = PROJECT_ROOT / "data" / "external" / "bundesliga_2324_benchmarks.csv"
REPORTS_DIR = PROJECT_ROOT / "data" / "reports"


def _as_1d_numeric(series) -> np.ndarray:
    """Force a single numeric 1-D array (handles duplicate column names)."""
    if isinstance(series, pd.DataFrame):
        series = series.iloc[:, 0]
    arr = pd.to_numeric(pd.Series(series).squeeze(), errors="coerce").to_numpy(dtype=float)
    return arr.reshape(-1)


def _spearman_pair(x, y) -> Tuple[float, float]:
    xa = _as_1d_numeric(x)
    ya = _as_1d_numeric(y)
    mask = np.isfinite(xa) & np.isfinite(ya)
    xa, ya = xa[mask], ya[mask]
    if len(xa) < 5 or np.std(xa) == 0 or np.std(ya) == 0:
        return float("nan"), float("nan")
    res = stats.spearmanr(xa, ya)
    if hasattr(res, "statistic"):
        return float(res.statistic), float(res.pvalue)
    r, p = res
    r_arr = np.asarray(r, dtype=float)
    p_arr = np.asarray(p, dtype=float)
    if r_arr.ndim == 0:
        return float(r_arr), float(p_arr)
    return float(r_arr[0, 1]), float(p_arr[0, 1])


def _minutes_est(n_actions: pd.Series, actions_per_minute: float) -> pd.Series:
    rate = max(actions_per_minute / 90.0, 1e-6)
    return n_actions / rate


def player_outcome_stats(events: pd.DataFrame, min_actions: int = 400) -> pd.DataFrame:
    """Per-player box-score style rates from events.parquet."""
    ev = events.dropna(subset=["player_id"]).copy()
    ev["player_id"] = ev["player_id"].astype(float)

    action_counts = ev.groupby("player_id").size().rename("n_events")
    apm = action_counts.sum() / max(len(ev) / 90.0, 1.0)

    goals = (
        ev[(ev["event_type"] == "Shot") & (ev["outcome"].astype(str).str.contains("Goal", case=False, na=False))]
        .groupby("player_id")
        .size()
        .rename("goals")
    )

    assists = pd.Series(dtype=float)
    if "pass_goal_assist" in ev.columns:
        assists = (
            ev[ev["pass_goal_assist"].fillna(False).astype(bool)]
            .groupby("player_id")
            .size()
            .rename("assists")
        )
    elif "shot_assist" in ev.columns:
        assists = (
            ev[ev["shot_assist"].fillna(False).astype(bool)]
            .groupby("player_id")
            .size()
            .rename("assists")
        )

    shots = ev[ev["event_type"] == "Shot"].groupby("player_id").size().rename("shots")

    xg_col = next((c for c in ("shot_xg", "shot_statsbomb_xg", "xg") if c in ev.columns), None)
    if xg_col:
        xg = ev[ev["event_type"] == "Shot"].groupby("player_id")[xg_col].sum().rename("xg_total")
    else:
        xg = pd.Series(dtype=float, name="xg_total")

    if "progressive" in ev.columns:
        prog = (
            ev[ev["progressive"].fillna(False).astype(bool)]
            .groupby("player_id")
            .size()
            .rename("progressive_actions")
        )
    else:
        prog = pd.Series(dtype=float, name="progressive_actions")

    out = pd.DataFrame({"player_id": action_counts.index, "n_events": action_counts.values})
    out["minutes_est"] = _minutes_est(out["n_events"], apm)
    out = out.set_index("player_id")
    for s in (goals, assists, shots, xg, prog):
        if len(s):
            out = out.join(s, how="left")
    out = out.fillna(0).reset_index()

    for col, per90 in (
        ("goals", "goals_per90"),
        ("assists", "assists_per90"),
        ("shots", "shots_per90"),
        ("xg_total", "xg_per90"),
        ("progressive_actions", "progressive_per90"),
    ):
        if col in out.columns:
            out[per90] = out[col] / out["minutes_est"].clip(lower=1) * 90.0

    if "goals_per90" in out.columns and "xg_per90" in out.columns:
        out["goals_plus_xg_per90"] = out["goals_per90"] + out["xg_per90"]
    elif "goals_per90" in out.columns:
        out["goals_plus_xg_per90"] = out["goals_per90"]

    out = out[out["n_events"] >= min_actions] if "n_events" in out.columns else out
    return out


def build_validation_table(
    board: Optional[pd.DataFrame] = None,
    events: Optional[pd.DataFrame] = None,
    min_actions: int = 400,
) -> pd.DataFrame:
    if board is None:
        board = enrich_leaderboard(load_leaderboard())
    if events is None:
        events = load_events()

    outcomes = player_outcome_stats(events, min_actions=min_actions)
    df = board.merge(outcomes, on="player_id", how="inner", suffixes=("", "_ev"))
    df = df.loc[:, ~df.columns.duplicated()].copy()

    for col in (
        "skm_per90",
        "delta_p_per90",
        "xt_per90",
        "goals_per90",
        "assists_per90",
        "xg_per90",
        "goals_plus_xg_per90",
        "progressive_per90",
    ):
        if col in df.columns:
            df[f"{col}_rank"] = df[col].rank(ascending=False, method="min")

    if "skm_per90_rank" in df.columns and "goals_plus_xg_per90_rank" in df.columns:
        df["skm_minus_outcome_rank"] = (
            df["goals_plus_xg_per90_rank"] - df["skm_per90_rank"]
        )

    return df


def spearman_matrix(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    """Pairwise Spearman correlations for numeric columns present in df."""
    present = [c for c in cols if c in df.columns]
    n = len(present)
    rho = np.full((n, n), np.nan)
    pval = np.full((n, n), np.nan)
    for i, a in enumerate(present):
        for j, b in enumerate(present):
            sub = df[[a, b]].dropna()
            if len(sub) < 5:
                continue
            r, p = _spearman_pair(sub[a], sub[b])
            rho[i, j] = r
            pval[i, j] = p
    return pd.DataFrame(rho, index=present, columns=present), pd.DataFrame(
        pval, index=present, columns=present
    )


def tier1_correlations(validation_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    cols = ["skm_per90", "delta_p_per90", "xt_per90"]
    return spearman_matrix(validation_df, cols)


def tier2_correlations(validation_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    cols = [
        "skm_per90",
        "delta_p_per90",
        "xt_per90",
        "goals_per90",
        "assists_per90",
        "xg_per90",
        "goals_plus_xg_per90",
        "progressive_per90",
    ]
    return spearman_matrix(validation_df, cols)


def load_external_benchmarks(path: Optional[Path] = None) -> Optional[pd.DataFrame]:
    p = path or EXTERNAL_BENCHMARKS
    if not p.exists():
        return None
    ext = pd.read_csv(p)
    if "player_name" not in ext.columns:
        return None
    return ext


def merge_external_benchmarks(
    validation_df: pd.DataFrame,
    external: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    ext = external if external is not None else load_external_benchmarks()
    if ext is None or ext.empty:
        return validation_df

    df = validation_df.copy()
    if "player" not in df.columns:
        return df

    merged = df.merge(
        ext,
        left_on="player",
        right_on="player_name",
        how="left",
    )
    rating_cols = [c for c in ext.columns if c.endswith("_rating") or c in ("fotmob_rating", "fbref_rating")]
    for col in rating_cols:
        if col in merged.columns:
            merged[f"{col}_rank"] = merged[col].rank(ascending=False, method="min")
            if "skm_per90_rank" in merged.columns:
                merged[f"skm_minus_{col}_rank"] = merged[f"{col}_rank"] - merged["skm_per90_rank"]
    return merged


def tier3_correlations(merged_df: pd.DataFrame) -> Optional[Tuple[pd.DataFrame, pd.DataFrame]]:
    rating_cols = [c for c in merged_df.columns if c.endswith("_rating") and not c.endswith("_rank")]
    if not rating_cols:
        return None
    cols = ["skm_per90"] + rating_cols
    return spearman_matrix(merged_df.dropna(subset=rating_cols, how="any"), cols)


def disagreement_table(
    merged_df: pd.DataFrame,
    rank_gap_col: str = "skm_minus_outcome_rank",
    min_gap: int = 15,
    top_n: int = 20,
) -> pd.DataFrame:
    if rank_gap_col not in merged_df.columns:
        return pd.DataFrame()
    sub = merged_df[merged_df[rank_gap_col].abs() >= min_gap].copy()
    return sub.sort_values(rank_gap_col, ascending=False).head(top_n)


def run_validation(
    output_dir: Optional[Path] = None,
    min_actions: int = 400,
) -> Dict[str, pd.DataFrame]:
    out = output_dir or REPORTS_DIR
    out.mkdir(parents=True, exist_ok=True)

    board = enrich_leaderboard(load_leaderboard())
    events = load_events()
    val = build_validation_table(board, events, min_actions=min_actions)

    results: Dict[str, pd.DataFrame] = {"validation_table": val}

    rho1, p1 = tier1_correlations(val)
    results["tier1_spearman"] = rho1
    rho1.to_csv(out / "tier1_spearman.csv")
    p1.to_csv(out / "tier1_spearman_pvalues.csv")

    rho2, p2 = tier2_correlations(val)
    results["tier2_spearman"] = rho2
    rho2.to_csv(out / "tier2_spearman.csv")
    p2.to_csv(out / "tier2_spearman_pvalues.csv")

    val.to_csv(out / "validation_player_table.csv", index=False)

    merged = merge_external_benchmarks(val)
    results["validation_with_external"] = merged
    merged.to_csv(out / "validation_with_external.csv", index=False)

    t3 = tier3_correlations(merged)
    if t3 is not None:
        rho3, p3 = t3
        results["tier3_spearman"] = rho3
        rho3.to_csv(out / "tier3_spearman.csv")
        p3.to_csv(out / "tier3_spearman_pvalues.csv")

    heroes = disagreement_table(merged, "skm_minus_outcome_rank", min_gap=10, top_n=25)
    if heroes.empty:
        heroes = disagreement_table(merged, "skm_minus_xt_rank", min_gap=10, top_n=25)
    heroes.to_csv(out / "validation_disagreements.csv", index=False)
    results["disagreements"] = heroes

    return results
