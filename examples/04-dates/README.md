# 04 — Dates

Dates are ambiguous to parse. `01/05/2025` could be the 5th of January or the
1st of May, and a parser that guesses can guess wrong, producing a date that is
not the one in the source. The framework does not guess: you state the exact
input format, and a value that doesn't match raises an error rather than being
misread. This example reformats some shipment timestamps to canonical forms, and
uses a malformed input to show the fail-fast behaviour.

## What it teaches

- **Reformatting with `convert_date`.** Parse a date with one format string and
  emit it in another.
- **Strict, fail-fast parsing.** A value that doesn't match the declared
  `source_format` raises an error rather than being guessed at.
- **No fuzzy / multi-format parser.** Each rule pins exactly one source format;
  a genuinely mixed column must be split and handled per format.

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
> malformed *values*. A bad date value always raises an error regardless of
> `--on-missing`.

## The rules, serialized

The full rule set for this example, in both formats. `RuleSet.save()` and `load()` (and the CLI's `--rules`) pick the format from the file extension (`.yaml`/`.yml` for YAML, otherwise JSON), and both load identically.

`rules.json`:

```json
[
  {
    "sources": [
      "ordered_at"
    ],
    "target": "order_date",
    "operations": [
      {
        "operation": "convert_date",
        "source_format": "%Y-%m-%d %H:%M:%S",
        "target_format": "%Y-%m-%d"
      }
    ],
    "metadata": {
      "rationale": "Reduce a full timestamp to a canonical date-only field; the time component is not needed downstream."
    }
  },
  {
    "sources": [
      "ordered_at"
    ],
    "target": "order_month",
    "operations": [
      {
        "operation": "convert_date",
        "source_format": "%Y-%m-%d %H:%M:%S",
        "target_format": "%b %Y"
      }
    ],
    "metadata": {
      "rationale": "Month-grain label for reporting/rollups, derived from the same timestamp."
    }
  },
  {
    "sources": [
      "delivered_on"
    ],
    "target": "delivered_us",
    "operations": [
      {
        "operation": "convert_date",
        "source_format": "%Y-%m-%d",
        "target_format": "%m/%d/%Y"
      }
    ],
    "metadata": {
      "rationale": "Reformat ISO date to US display format. Source is date-only, so the source_format has no time component."
    }
  }
]
```

`rules.yaml`:

```yaml
- sources: [ordered_at]
  target: order_date
  operations:
  - {operation: convert_date, source_format: '%Y-%m-%d %H:%M:%S', target_format: '%Y-%m-%d'}
  metadata: {rationale: Reduce a full timestamp to a canonical date-only field; the
      time component is not needed downstream.}

- sources: [ordered_at]
  target: order_month
  operations:
  - {operation: convert_date, source_format: '%Y-%m-%d %H:%M:%S', target_format: '%b
      %Y'}
  metadata: {rationale: 'Month-grain label for reporting/rollups, derived from the
      same timestamp.'}

- sources: [delivered_on]
  target: delivered_us
  operations:
  - {operation: convert_date, source_format: '%Y-%m-%d', target_format: '%m/%d/%Y'}
  metadata: {rationale: 'Reformat ISO date to US display format. Source is date-only,
      so the source_format has no time component.'}
```

## Running it

```bash
../../../harmonization-framework/venv/bin/python build_rules.py
../../../harmonization-framework/venv/bin/python run_python.py
../../../harmonization-framework/venv/bin/python run_yaml.py   # same, from rules.yaml
bash run_cli.sh
```

## Expected output

```
...,order_date,order_month,delivered_us,...
...,2025-01-05,Jan 2025,01/08/2025,...
```
