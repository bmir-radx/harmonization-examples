#!/usr/bin/env bash
# Example 01 — run via the harmonize CLI (no Python knowledge required).
#
# The CLI consumes the SAME rules.json that build_rules.py produced. Unlike the
# Python `harmonize_file` API, the CLI emits ONLY the target columns; pass
# --include-metadata to also get the `source dataset` / `original_id` columns.
#
# We invoke the CLI via `python -m` against the framework's venv so this runs
# without needing the `harmonize` entry point on your PATH. If you've installed
# the framework, you can equivalently just run: harmonize --rules ... etc.
set -euo pipefail
cd "$(dirname "$0")"

PY=../../../harmonization-framework/venv/bin/python

"$PY" -m harmonization_framework.cli \
  --rules rules.json \
  --input input.csv \
  --output output_cli.csv \
  --dataset-name hello \
  --include-metadata \
  --on-missing error

echo "Wrote output_cli.csv (target columns only):"
cat output_cli.csv
