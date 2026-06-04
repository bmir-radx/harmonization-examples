# 02 — Units & Numbers

Numeric harmonization, with one big lesson: **the order of operations in a rule
changes the result.**

## What it teaches

- `convert_units` — unit conversion via `pint` (inches → cm).
- `scale` — multiply by a factor (lb → kg).
- `round` vs. `format_number` — round keeps a number; format_number pins a
  presentation **string** with fixed decimals.
- `threshold` — clamp values into a valid range.
- `bin` — bucket a numeric value into labeled bands (requires integer bounds).

## The data

`input.csv` holds mixed-unit vitals: `age` (years), `height_in` (inches),
`weight_lb` (pounds), `oxygen_saturation` (percent, with one bad reading).

## The harmonization choices (and why)

| Source | Target | Pipeline | Why this order |
|--------|--------|----------|----------------|
| `height_in` | `height_cm` | `convert_units(inch→cm)` → `round(1)` | Convert at full precision **first**, round for display **second**. Rounding inches first would amplify error when scaled up. |
| `weight_lb` | `weight_kg` | `scale(0.45359237)` → `format_number(2)` | Scale to kg, then pin a 2-decimal **string** (`"23.59"`). `format_number` last because it's a display contract, and it returns a string. |
| `oxygen_saturation` | `spo2_clamped` | `threshold(0, 100)` | SpO2 can't exceed 100%; `101` is a sensor artifact. Clamp deterministically rather than dropping the row. |
| `age` | `age_band` | `bin(child/adolescent/adult/older_adult)` | Inclusive, non-overlapping integer ranges tiling 0..120 so every age lands in exactly one band. |

### Why order matters — a concrete contrast

`convert_units → round` gives `48.5 in → 123.2 cm`. Swap them and you'd round
`48.5` (no change here) but in general you'd round the *input unit* and lose
precision the conversion then magnifies. The rule pipeline is ordered for a
reason; each example states that reason in the rule's `metadata.rationale`.

### Notable result

Subject `S3` has `oxygen_saturation = 101`, which `threshold(0, 100)` clamps to
`100.0` in `spo2_clamped` — a visible, auditable correction.

## Running it

```bash
../../../harmonization-framework/venv/bin/python build_rules.py   # regenerate rules.json
../../../harmonization-framework/venv/bin/python run_python.py     # run + assert golden output
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
