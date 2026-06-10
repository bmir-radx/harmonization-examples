# 02 — Units & Numbers

This example harmonizes a few mixed-unit vital signs, introducing the numeric
primitives: unit conversion, scaling, rounding, formatting, clamping, and
binning. Several rules chain two of these, where the order is chosen for a
reason — converting at full precision before rounding for display, for instance
— and each rule's rationale records that choice.

## What it teaches

- **Unit conversion and scaling.** `convert_units` converts between real units
  (inches → cm), and `scale` multiplies by a factor (lb → kg).
- **Rounding vs. formatting.** `round` keeps a *number* with fewer decimals;
  `format_number` pins a presentation *string* with fixed decimals — a display
  contract, not a numeric one.
- **Clamping and binning.** `threshold` forces a value into a valid range, and
  `bin` buckets a numeric value into labelled bands (with integer bounds).

## The data

`input.csv` holds mixed-unit vitals: `age` (years), `height_in` (inches),
`weight_lb` (pounds), `oxygen_saturation` (percent, with one bad reading).

## The harmonization choices (and why)

| Source | Target | Pipeline | Why |
|--------|--------|----------|-----|
| `height_in` | `height_cm` | `convert_units(inch→cm)` → `round(1)` | Convert at full precision **first**, round for display **second**. Rounding inches first would amplify error when scaled up. |
| `weight_lb` | `weight_kg` | `scale(0.45359237)` → `format_number(2)` | Scale to kg, then pin a 2-decimal **string** (`"23.59"`). `format_number` last because it's a display contract, and it returns a string. |
| `oxygen_saturation` | `spo2_clamped` | `threshold(0, 100)` | SpO2 can't exceed 100%; `101` is a sensor artifact. Clamp deterministically rather than dropping the row. |
| `age` | `age_band` | `bin(child/adolescent/adult/older_adult)` | Inclusive, non-overlapping integer ranges tiling 0..120 so every age lands in exactly one band. |

### Notable result

Subject `S3` has `oxygen_saturation = 101`, which `threshold(0, 100)` clamps to
`100.0` in `spo2_clamped` — a visible, auditable correction.

## The rules, serialized

As in example 01, the saved file *is* the mapping, and the same rule set
serializes to JSON (the default) or YAML — the extension decides which, and
both load identically. Shown in both formats below.

Worth noticing here is how the numeric primitives look once written out: each
`convert_units`, `scale`, `round`, `bin`, `threshold`, and `format_number`
records its parameters inline, so the file states exactly which conversion
factor, how many decimals, or which bin edges were used.

`rules.json`:

```json
[
  {
    "sources": [
      "height_in"
    ],
    "target": "height_cm",
    "operations": [
      {
        "operation": "convert_units",
        "source_unit": "inch",
        "target_unit": "cm"
      },
      {
        "operation": "round",
        "precision": 1
      }
    ],
    "metadata": {
      "rationale": "Convert at full precision, then round. Rounding before the conversion would amplify rounding error."
    }
  },
  {
    "sources": [
      "weight_lb"
    ],
    "target": "weight_kg",
    "operations": [
      {
        "operation": "scale",
        "scaling_factor": 0.45359237
      },
      {
        "operation": "format_number",
        "precision": 2
      }
    ],
    "metadata": {
      "rationale": "Scale to kg, then FormatNumber(2) to pin a stable 2-decimal string for display/export."
    }
  },
  {
    "sources": [
      "oxygen_saturation"
    ],
    "target": "spo2_clamped",
    "operations": [
      {
        "operation": "threshold",
        "lower": 0.0,
        "upper": 100.0
      }
    ],
    "metadata": {
      "rationale": "SpO2 > 100% is physically impossible (sensor artifact); clamp to [0,100] deterministically instead of dropping the row."
    }
  },
  {
    "sources": [
      "age"
    ],
    "target": "age_band",
    "operations": [
      {
        "operation": "bin",
        "bins": [
          {
            "label": "child",
            "start": 0,
            "end": 12
          },
          {
            "label": "adolescent",
            "start": 13,
            "end": 17
          },
          {
            "label": "adult",
            "start": 18,
            "end": 64
          },
          {
            "label": "older_adult",
            "start": 65,
            "end": 120
          }
        ]
      }
    ],
    "metadata": {
      "rationale": "Coarse life-stage bands with inclusive, non-overlapping integer ranges covering 0..120."
    }
  }
]
```

`rules.yaml`:

```yaml
- sources: [height_in]
  target: height_cm
  operations:
  - {operation: convert_units, source_unit: inch, target_unit: cm}
  - {operation: round, precision: 1}
  metadata: {rationale: 'Convert at full precision, then round. Rounding before the
      conversion would amplify rounding error.'}

- sources: [weight_lb]
  target: weight_kg
  operations:
  - {operation: scale, scaling_factor: 0.45359237}
  - {operation: format_number, precision: 2}
  metadata: {rationale: 'Scale to kg, then FormatNumber(2) to pin a stable 2-decimal
      string for display/export.'}

- sources: [oxygen_saturation]
  target: spo2_clamped
  operations:
  - {operation: threshold, lower: 0.0, upper: 100.0}
  metadata: {rationale: 'SpO2 > 100% is physically impossible (sensor artifact); clamp
      to [0,100] deterministically instead of dropping the row.'}

- sources: [age]
  target: age_band
  operations:
  - operation: bin
    bins:
    - {label: child, start: 0, end: 12}
    - {label: adolescent, start: 13, end: 17}
    - {label: adult, start: 18, end: 64}
    - {label: older_adult, start: 65, end: 120}
  metadata: {rationale: 'Coarse life-stage bands with inclusive, non-overlapping integer
      ranges covering 0..120.'}
```

## Running it

```bash
../../../harmonization-framework/venv/bin/python build_rules.py   # regenerate rules.json + rules.yaml
../../../harmonization-framework/venv/bin/python run_python.py     # run + assert golden master
../../../harmonization-framework/venv/bin/python run_yaml.py       # same, loading rules.yaml
bash run_cli.sh                                                    # CLI (target columns only)
```

## Expected output

`expected_output.csv` (Python API — all columns):

```
subject_id,age,height_in,weight_lb,oxygen_saturation,height_cm,weight_kg,spo2_clamped,age_band,source dataset,original_id
S1,7,48.5,52.0,98,123.2,23.59,98.0,child,vitals,0
S3,62,66.0,210.7,101,167.6,95.57,100.0,adult,vitals,2
...
```

The CLI emits only `height_cm, weight_kg, spo2_clamped, age_band` (+ metadata
with `--include-metadata`).
