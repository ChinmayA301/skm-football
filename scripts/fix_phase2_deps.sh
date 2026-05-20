#!/usr/bin/env bash
# Phase 2 fixes: multimethod + broken lightgbm/xgboost (libomp) on Mac without Homebrew
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate

echo "=== multimethod (pandera/socceraction) ==="
pip install "multimethod>=1.8,<2.0"

echo "=== remove broken boosters (libomp) ==="
pip uninstall -y lightgbm xgboost catboost 2>/dev/null || true

echo "=== reinstall skm code (pick up vaep_delta fix) ==="
pip install -e ".[model]" --no-deps --force-reinstall

echo "=== verify source has sklearn VAEP default ==="
grep -q "SklearnVAEP" src/skm/models/vaep_delta.py || { echo "ERROR: vaep_delta.py missing SklearnVAEP"; exit 1; }
grep -q "SKM_VAEP_USE_BOOSTERS" src/skm/models/vaep_delta.py || { echo "ERROR: vaep_delta.py missing booster opt-in"; exit 1; }
echo "vaep_delta.py OK"

python -c "
from multimethod import overload
from socceraction.data.statsbomb import StatsBombLoader
print('StatsBombLoader OK')
"

echo ""
echo "Run: skm-build-scores --max-games 5"
