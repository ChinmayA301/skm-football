#!/usr/bin/env python3
"""Print top N players from validation table for Tier 3 FotMob lookups."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
VALIDATION_CSV = ROOT / "data" / "reports" / "validation_player_table.csv"
EVENTS = ROOT / "data" / "processed" / "events.parquet"
LEADERBOARD = ROOT / "data" / "processed" / "player_leaderboard.parquet"


def main() -> int:
    parser = argparse.ArgumentParser(description="Top SKM players for external benchmark lookup")
    parser.add_argument("-n", "--top", type=int, default=10, help="Number of players (default 10)")
    parser.add_argument(
        "--sort",
        default="skm_per90",
        choices=["skm_per90", "delta_p_per90", "xt_per90", "skm_minus_outcome_rank"],
        help="Sort column",
    )
    args = parser.parse_args()

    if VALIDATION_CSV.exists():
        df = pd.read_csv(VALIDATION_CSV)
    elif LEADERBOARD.exists():
        print("Note: run skm-validate first for full columns; using leaderboard only.\n")
        df = pd.read_parquet(LEADERBOARD)
    else:
        print("Missing data. Run: skm-build-scores && skm-validate", file=sys.stderr)
        return 1

    if "player" not in df.columns and EVENTS.exists():
        names = pd.read_parquet(EVENTS).dropna(subset=["player_id"]).groupby("player_id")["player"].first()
        df["player"] = df["player_id"].map(names)

    sort_col = args.sort if args.sort in df.columns else "skm_per90"
    top = df.nlargest(args.top, sort_col)

    show = [
        c
        for c in [
            "player",
            "player_id",
            "skm_per90",
            "delta_p_per90",
            "xt_per90",
            "goals_per90",
            "xg_per90",
            "goals_plus_xg_per90",
            "skm_minus_outcome_rank",
            "n_actions",
        ]
        if c in top.columns
    ]
    print(top[show].to_string(index=False))
    print("\n--- Copy this table (or player names) for Tier 3 / blog prioritization ---")
    if "player" in top.columns:
        print("\nNames only (for bundesliga_2324_benchmarks.csv):")
        for name in top["player"].dropna():
            print(f"  {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
