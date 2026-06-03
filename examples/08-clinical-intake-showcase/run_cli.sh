#!/usr/bin/env bash
# Example 08 — run via the harmonize CLI. Same rules.json, target columns only.
#
# Note --on-missing error: this intake has all expected source columns, so we
# fail loudly if any are absent rather than silently skipping rules. Switch to
# `warn` or `skip` to harmonize a partial file (see example 07).
set -euo pipefail
cd "$(dirname "$0")"

PY=../../../harmonization-framework/venv/bin/python

"$PY" -m harmonization_framework.cli \
  --rules rules.json \
  --input input.csv \
  --output output_cli.csv \
  --dataset-name intake \
  --include-metadata \
  --on-missing error

echo "Wrote output_cli.csv (target columns only):"
cat output_cli.csv
