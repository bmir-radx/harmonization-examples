#!/usr/bin/env bash
# Example 04 — run via the harmonize CLI. Same rules.json, target columns only.
set -euo pipefail
cd "$(dirname "$0")"

PY=../../../harmonization-framework/venv/bin/python

"$PY" -m harmonization_framework.cli \
  --rules rules.json \
  --input input.csv \
  --output output_cli.csv \
  --dataset-name events \
  --include-metadata \
  --on-missing error

echo "Wrote output_cli.csv (target columns only):"
cat output_cli.csv
