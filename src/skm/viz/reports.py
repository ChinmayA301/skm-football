"""Export static validation plots to data/reports/."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from skm.config import PROJECT_ROOT
from skm.viz.hidden_heroes import hidden_heroes_table, role_fairness_by_type
from skm.viz.loaders import DataNotFoundError, load_all
from skm.viz.plots import plot_leaderboard_bar, plot_match_timeline, plot_scatter_validation
from skm.viz.timeline import list_match_ids, match_timeline_data
from skm.viz.validation import run_validation

REPORTS_DIR = PROJECT_ROOT / "data" / "reports"


def export_reports(
    output_dir: Optional[Path] = None,
    top_n: int = 15,
) -> Path:
    out = output_dir or REPORTS_DIR
    out.mkdir(parents=True, exist_ok=True)

    actions, events, board = load_all()

    plot_leaderboard_bar(
        board,
        metric="skm_per90",
        top_n=top_n,
        output_path=out / "leaderboard_skm_per90.png",
    )

    plot_leaderboard_bar(
        board,
        metric="delta_p_per90",
        top_n=top_n,
        title=f"Top {top_n} by VAEP (ΔP) per 90",
        output_path=out / "leaderboard_delta_p_per90.png",
    )

    heroes = hidden_heroes_table(board, actions, events, top_n=top_n)
    heroes.to_csv(out / "hidden_heroes.csv", index=False)

    fairness = role_fairness_by_type(actions)
    fairness.to_csv(out / "skm_by_action_type.csv", index=False)

    match_ids = list_match_ids(actions)
    if match_ids:
        mid = match_ids[0]
        team_cum, goals = match_timeline_data(mid, actions)
        plot_match_timeline(
            team_cum,
            goals,
            title=f"Match {mid} — cumulative SKM",
            output_path=out / f"timeline_match_{mid}.png",
        )

    val_results = run_validation(out)
    val = val_results["validation_table"]
    if "skm_per90" in val.columns and "goals_plus_xg_per90" in val.columns:
        plot_scatter_validation(
            val,
            x_col="goals_plus_xg_per90",
            y_col="skm_per90",
            output_path=out / "scatter_skm_vs_goals_xg.png",
            title="SKM per 90 vs goals+xG per 90",
        )
    if "skm_per90" in val.columns and "delta_p_per90" in val.columns:
        plot_scatter_validation(
            val,
            x_col="delta_p_per90",
            y_col="skm_per90",
            output_path=out / "scatter_skm_vs_delta_p.png",
            title="SKM per 90 vs VAEP (ΔP) per 90",
        )

    return out


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Export SKM validation plots")
    parser.add_argument("--output", type=str, default=str(REPORTS_DIR))
    parser.add_argument("--top-n", type=int, default=15)
    args = parser.parse_args(argv)

    try:
        path = export_reports(Path(args.output), top_n=args.top_n)
        print(f"Reports written to {path}")
        return 0
    except DataNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
