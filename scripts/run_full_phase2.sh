#!/usr/bin/env bash
# Full Phase 2 on the default single competition (Bundesliga 2023/24).
# For the full 216-match multi-competition sample used in docs/RESULTS.md, run:
#   skm-build-scores --competitions "1. Bundesliga:2023/2024,FIFA World Cup:2022,UEFA Euro:2024,Ligue 1:2022/2023,La Liga:2020/2021"
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
echo "Building SKM scores for the default open-data sample..."
skm-build-scores
echo "Done. Outputs:"
ls -la data/processed/actions_scored.parquet data/processed/player_leaderboard.parquet
