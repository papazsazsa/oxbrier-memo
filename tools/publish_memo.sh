#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

message="${1:-Update opportunity memo}"

python3 tools/build_memo.py

git add index.html README.md .gitignore tools/build_memo.py tools/publish_memo.sh

if git diff --cached --quiet; then
  echo "No new memo site changes to commit. Pushing any unpushed commits."
  git push origin main
  exit 0
fi

git commit -m "$message"
git push origin main
