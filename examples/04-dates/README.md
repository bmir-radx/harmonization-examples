# 04 — Dates

Normalizing date/time fields to canonical formats.

## What it teaches

- `convert_date` — `strptime`/`strftime` reformatting.
- Its **strict, fail-fast** behaviour: a value that doesn't match
  `source_format` raises rather than guessing.
- That the framework has **no fuzzy/multi-format parser** — each rule pins one
  exact source format.

## The data

`input.csv` — shipment timestamps in one consistent source format:

| shipment_id | ordered_at | delivered_on |
|-------------|-----------|--------------|
| SH1 | `2025-01-05 09:30:00` | `2025-01-08` |
| … | … | … |

## The harmonization choices (and why)

| Source | Target | Conversion | Why |
|--------|--------|-----------|-----|
| `ordered_at` | `order_date` | `%Y-%m-%d %H:%M:%S` → `%Y-%m-%d` | Drop time-of-day to a canonical date. |
| `ordered_at` | `order_month` | `%Y-%m-%d %H:%M:%S` → `%b %Y` | Month-grain label (`Jan 2025`) for rollups, from the same column. |
| `delivered_on` | `delivered_us` | `%Y-%m-%d` → `%m/%d/%Y` | US display format; source is date-only, so no time in the source format. |

## Fail-fast is a feature

`convert_date` does not try to be clever. Run it against `bad_input.csv` (a row
with `01/05/2025 9:30 AM`, which doesn't match `%Y-%m-%d %H:%M:%S`):

```bash
../../../harmonization-framework/venv/bin/python -c "
from harmonization_framework import RuleSet
from harmonization_framework.harmonize import harmonize_file
r=RuleSet(); r.load('rules.json', clean=True)
harmonize_file('bad_input.csv','/tmp/out.csv', r, dataset_name='events')
"
```

You get:

```
ValueError: Failed to parse date/time value '01/05/2025 9:30 AM' with source_format='%Y-%m-%d %H:%M:%S'
```

A silent misparse (guessing month vs. day) would corrupt data quietly; a loud
error is the safer default for a meaningful field. If a column genuinely mixes
formats, split it (e.g. by a flag column) and apply a `convert_date` per format
— there is no single multi-format rule.

> **`--on-missing` is unrelated.** That CLI flag governs missing *columns*, not
> malformed *values*. A bad date value always raises regardless of
> `--on-missing`.

## Running it

```bash
../../../harmonization-framework/venv/bin/python build_rules.py
../../../harmonization-framework/venv/bin/python run_python.py
bash run_cli.sh
```

## Expected output

```
...,order_date,order_month,delivered_us,...
...,2025-01-05,Jan 2025,01/08/2025,...
```
