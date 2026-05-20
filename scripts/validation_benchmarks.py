#!/usr/bin/env python3
"""Run Tier 1–3 validation and export reports to data/reports/."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running without install
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skm.viz.loaders import DataNotFoundError
from skm.viz.plots import plot_scatter_validation
from skm.viz.validation import REPORTS_DIR, run_validation


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description="SKM validation benchmarks")
    parser.add_argument("--output", type=str, default=str(REPORTS_DIR))
    parser.add_argument("--min-actions", type=int, default=400)
    args = parser.parse_args(argv)

    try:
        results = run_validation(Path(args.output), min_actions=args.min_actions)
    except DataNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    val = results["validation_table"]
    out = Path(args.output)

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

    print("\n=== Tier 1 Spearman (SKM vs ΔP, xT) ===")
    print(results["tier1_spearman"].round(3).to_string())

    print("\n=== Tier 2 Spearman (SKM vs outcomes) ===")
    print(results["tier2_spearman"].round(3).to_string())

    if "tier3_spearman" in results:
        print("\n=== Tier 3 Spearman (SKM vs public ratings) ===")
        print(results["tier3_spearman"].round(3).to_string())
    else:
        print(
            "\nTier 3: no external benchmarks — add data/external/bundesliga_2324_benchmarks.csv"
        )

    print(f"\nWrote reports to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
