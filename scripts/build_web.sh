#!/usr/bin/env sh
# Bundle web/js/main.js into web/app.js, a single classic script that also runs from file://.
# Re-run after editing anything in web/js/, and commit app.js.
set -eu
cd "$(dirname "$0")/.."
pnpm dlx esbuild@0.25.0 web/js/main.js --bundle --format=iife --target=es2020 --outfile=web/app.js --log-level=warning
echo "Built web/app.js"
