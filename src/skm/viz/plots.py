"""Matplotlib / Plotly figure builders."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd


def plot_match_timeline(
    team_cum: pd.DataFrame,
    goals: pd.DataFrame,
    team_names: Optional[dict] = None,
    title: str = "Cumulative SKM by team",
    output_path: Optional[Path] = None,
) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(10, 5))

    for team_id, grp in team_cum.groupby("team_id"):
        label = team_names.get(team_id, str(team_id)) if team_names else str(team_id)
        ax.plot(grp["minute"], grp["skm_cum"], label=label, linewidth=2)

    for _, g in goals.iterrows():
        ax.axvline(g["minute"], color="gray", linestyle="--", alpha=0.5)

    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_xlabel("Minute")
    ax.set_ylabel("Cumulative SKM")
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=120)
    return fig


def plot_leaderboard_bar(
    board: pd.DataFrame,
    metric: str = "skm_per90",
    top_n: int = 15,
    title: Optional[str] = None,
    output_path: Optional[Path] = None,
) -> plt.Figure:
    data = board.nlargest(top_n, metric).iloc[::-1]
    labels = data["player"].fillna(data["player_id"].astype(str)) if "player" in data else data["player_id"]

    fig, ax = plt.subplots(figsize=(8, max(4, top_n * 0.35)))
    ax.barh(labels.astype(str), data[metric], color="steelblue")
    ax.set_xlabel(metric)
    ax.set_title(title or f"Top {top_n} by {metric}")
    fig.tight_layout()

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=120)
    return fig


def plot_scatter_validation(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str = "SKM validation",
    output_path: Optional[Path] = None,
) -> plt.Figure:
    cols = [x_col, y_col]
    if "player" in df.columns:
        cols.append("player")
    sub = df[cols].dropna()
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(sub[x_col], sub[y_col], alpha=0.7, s=40)
    if "player" in sub.columns and len(sub) <= 30:
        for _, row in sub.iterrows():
            ax.annotate(str(row["player"])[:12], (row[x_col], row[y_col]), fontsize=7, alpha=0.8)
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=120)
    return fig
