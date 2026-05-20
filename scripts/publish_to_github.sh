#!/usr/bin/env bash
# Publish to GitHub using git only (no Homebrew, no gh required)
set -euo pipefail
cd "$(dirname "$0")/.."

REPO_NAME="${1:-skm-football}"
GITHUB_USER="${2:-}"

if [[ -z "$GITHUB_USER" ]]; then
  echo "Enter your GitHub username:"
  read -r GITHUB_USER
fi

# Empty or broken .git (e.g. placeholder dir) must be re-initialized
if ! git rev-parse --is-inside-work-tree &>/dev/null; then
  if [[ -d .git ]]; then
    echo "Removing invalid .git directory..."
    rm -rf .git
  fi
  git init -b main
fi

git add -A
if git diff --cached --quiet 2>/dev/null && [[ -z "$(git status --porcelain 2>/dev/null)" ]]; then
  echo "Nothing to commit."
else
  git commit -m "$(cat <<'EOF'
SKM v1: action-level metric and validation harness.

StatsBomb ingest, VAEP ΔP + D/C/R combine, Streamlit dashboard,
Tier 1–3 validation, and docs/ROADMAP for moment-based unified SKM.
EOF
)" || true
fi

REMOTE="https://github.com/${GITHUB_USER}/${REPO_NAME}.git"

if git remote get-url origin &>/dev/null; then
  echo "Remote origin already set."
else
  git remote add origin "$REMOTE"
fi

echo ""
echo "=== Next steps (no brew, no gh) ==="
echo ""
echo "1. Create an empty repo in your browser:"
echo "   https://github.com/new"
echo "   Name: ${REPO_NAME}"
echo "   Do NOT add README or .gitignore (this project has them)"
echo ""
echo "2. Push:"
echo "   git push -u origin main"
echo ""
echo "   If SSH:"
echo "   git remote set-url origin git@github.com:${GITHUB_USER}/${REPO_NAME}.git"
echo "   git push -u origin main"
echo ""

# Optional: use gh if already installed (not via brew)
if command -v gh &>/dev/null; then
  echo "gh found — attempting create + push..."
  gh repo create "${GITHUB_USER}/${REPO_NAME}" --public --source=. --remote=origin --push 2>/dev/null && exit 0
  echo "gh create failed; use manual steps above."
fi
