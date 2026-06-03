# 08 — Clinical Intake Showcase

A realistic, end-to-end example. Where the tutorials isolate one idea each, this
one harmonizes a messy intake CSV the way you'd actually have to, and focuses on
the **decisions** — fail vs. coerce vs. default, and many-to-one mapping.

## The data (and its messes)

`input.csv`:

| mrn | patient_name | visit_code | visit_date | height_in | consent_research | consent_biobank | consent_none |
|-----|--------------|-----------|-----------|-----------|------|------|------|
| 1001 | `Lovelace, Ada` | BL | 2025-01-14 | 64.5 | 1 | 0 | 0 |
| 1002 | `  turing,  alan ` | FU | 2025-02-03 | 70.0 | 0 | 1 | 0 |
| 1003 | `Hopper, Grace` | SC | 2025-02-20 | 66.25 | 0 | 0 | 1 |
| 1004 | `Johnson, Katherine` | **XX** | 2025-03-01 | 61.0 | 1 | 0 | 0 |

The deliberate messes: `"Last, First"` names with inconsistent whitespace/case
(row 1002), a visit code outside the controlled set (`XX`, row 1004), dates in a
non-target format, height in inches, and consent split across three one-hot
columns.

## The harmonization decisions (and why)

| Source(s) | Target | Pipeline | Decision |
|-----------|--------|----------|----------|
| `patient_name` | `family_name` | `substitute(before comma)` → `normalize_text(lower)` | Define the field, then clean casing/whitespace. |
| `patient_name` | `given_name` | `substitute(after comma)` → `normalize_text(lower)` | Two rules on one column = split a field. |
| `visit_code` | `visit_type` | `enum_to_enum(default="unmapped")` | **Coerce + flag.** `XX` → `"unmapped"` so the batch survives and the anomaly stays visible. |
| `visit_date` | `visit_date_us` | `convert_date(%Y-%m-%d → %m/%d/%Y)` | **Fail fast.** A malformed date raises — a silent misparse is worse than a loud error for a clinical field. |
| `height_in` | `height_cm` | `convert_units(inch→cm)` → `round(1)` | Convert at full precision, then round. |
| `consent_research`, `consent_biobank`, `consent_none` | `consent_type` | `reduce(one-hot)` → `enum_to_enum(default="ambiguous", int keys)` | **Many-to-one**: collapse three flags to one label (below). |

### Contrast worth noting: fail vs. coerce

The same file makes *both* choices on purpose. The visit code is a
non-critical label, so we coerce the unknown `XX` to `"unmapped"`. The date is
clinically meaningful, so we let `convert_date` fail fast on anything
malformed. Harmonization isn't "always coerce" or "always fail" — it's choosing
per field, and recording why (here, in each rule's `metadata.rationale`).

### The many-to-one consent reduction

Three mutually exclusive one-hot flags collapse into one `consent_type`:

1. `reduce(one-hot)` returns the index of the single set bit (`0`/`1`/`2`), or
   `None` if zero or multiple flags are set.
2. `enum_to_enum` names it (keyed by integers `0`/`1`/`2`), with
   `default="ambiguous"` for the `None` case.

The integer index feeds `enum_to_enum` directly — no cast in between. The map is
keyed by integers, and `EnumToEnum` serializes its mapping as a list of
`{"from", "to"}` entries, so those integer keys keep their type through a
`save()`/`load()` and match the index identically in-memory and from
`rules.json`. (See example 05 for why the entry-list form matters: a JSON object
would have coerced the integer keys to strings and the index would have missed
every key.)

> Earlier versions of these examples needed a `cast(integer → text)` here, to
> dodge exactly that coercion — and the golden-output check caught it when the
> first attempt produced `ambiguous` for every row. The serialization format now
> preserves key types, so the cast is gone; the self-checking
> `expected_output.csv` still guards the result.

## Running it

```bash
../../../harmonization-framework/venv/bin/python build_rules.py
../../../harmonization-framework/venv/bin/python run_python.py   # run + assert
bash run_cli.sh
node client.ts                                                   # start the sidecar first
```

## Expected output

`expected_output.csv` (Python / sidecar — all columns) ends with the harmonized
fields:

```
...,family_name,given_name,visit_type,visit_date_us,height_cm,consent_type,source dataset,original_id
...,lovelace,ada,baseline,01/14/2025,163.8,research,intake,0
...,turing,alan,follow_up,02/03/2025,177.8,biobank,intake,1
...,hopper,grace,screening,02/20/2025,168.3,declined,intake,2
...,johnson,katherine,unmapped,03/01/2025,154.9,research,intake,3
```

Row 1004's `unmapped` visit type is the visible trace of the coerce-and-flag
decision.
