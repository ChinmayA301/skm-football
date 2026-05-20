#!/usr/bin/env bash
# Full Phase 2 on all open-data matches (34-match Bundesliga sample)
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
echo "Building SKM scores for full Bundesliga 2023/24 sample..."
skm-build-scores
echo "Done. Outputs:"
ls -la data/processed/actions_scored.parquet data/processed/player_leaderboard.parquet
