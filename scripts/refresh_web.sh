#!/usr/bin/env sh
# Refresh the static site: export finished runs to web/data/, rebuild web/app.js, run the web tests.
# Pass --data-only to skip the bundle and tests (enough when only the stored results changed).
set -eu
cd "$(dirname "$0")/.."

uv run python scripts/export_web_data.py
if [ "${1:-}" != "--data-only" ]; then
  ./scripts/build_web.sh
  node --test "tests/web/*.test.mjs"
fi
echo "Site refreshed. Review with 'git diff --stat web/', then commit web/data and web/app.js."
