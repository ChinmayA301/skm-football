#!/usr/bin/env bash
# Setup venv — no Homebrew. Uses pre-built wheels only (fixes scipy build errors on Python 3.9).
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== 1/4: Create venv ==="
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip wheel

echo "=== 2/4: Core wheels (Phase 1) ==="
pip install --only-binary=:all: \
  "numpy>=1.26.0,<2.0.0" \
  "pandas>=2.0,<2.3" \
  "pyarrow>=17" \
  "scipy>=1.13.1,<1.15" \
  "scikit-learn>=1.4.2,<1.6"

pip install statsbombpy tqdm python-dotenv hatchling
pip install -e ".[dev]"

python -c "import numpy, pandas; print('Phase 1 deps OK')"

echo "=== 3/4: Phase 2 + app (ML libs) ==="
pip install "socceraction>=1.5.0"
pip install "multimethod>=1.8,<2.0"

# VAEP uses sklearn GBM fallback if xgboost/lightgbm fail (no libomp on Mac without Homebrew)
echo "VAEP will use sklearn if boosters unavailable (no brew needed)"

pip install "streamlit>=1.28" "plotly>=5.18" "matplotlib>=3.8"
pip install -e ".[model,app]" --no-deps 2>/dev/null || pip install -e ".[model,app]"

echo "=== 4/4: Verify ==="
python -c "
import numpy, pandas, scipy, sklearn
print('numpy', numpy.__version__)
print('pandas', pandas.__version__)
print('scipy', scipy.__version__)
"
echo ""
echo "Done. Run:"
echo "  source .venv/bin/activate"
echo "  skm-build-events          # Phase 1"
echo "  skm-build-scores --max-games 5   # Phase 2 test"
