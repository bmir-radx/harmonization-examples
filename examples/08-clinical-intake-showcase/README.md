# 08 — Clinical Intake Showcase

An end-to-end example that combines the primitives from the earlier chapters on
one input. Where each earlier chapter isolates a single idea, this one
harmonizes an intake CSV with several different problems at once — name
reshaping, an out-of-vocabulary code, a date reformat, a unit conversion, and a
multi-column consent reduction. The focus is on the **decisions**: when to fail
on a bad value and when to coerce it, and how to collapse several columns into
one.

## What it teaches

- **Combining primitives on real input.** `substitute`, `normalize_text`,
  `enum_to_enum`, `convert_date`, `convert_units`, `round`, and `reduce` applied
  together on one file.
- **Fail vs. coerce, per field.** The same file lets a clinically meaningful
  date fail fast while coercing a non-critical out-of-vocabulary code to a
  flagged value.
- **Many-to-one reduction.** Three one-hot consent columns collapse to a single
  `consent_type` label.

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
| `visit_date` | `visit_date_us` | `convert_date(%Y-%m-%d → %m/%d/%Y)` | **Fail fast.** A malformed date raises an error — a silent misparse is worse than a loud error for a clinical field. |
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
`rules.json`. (See chapter 05 for why the entry-list form matters: a JSON object
would have coerced the integer keys to strings and the index would have missed
every key.)

> Earlier versions of these examples needed a `cast(integer → text)` here, to
> dodge exactly that coercion — and the golden-output check caught it when the
> first attempt produced `ambiguous` for every row. The serialization format now
> preserves key types, so the cast is gone; the self-checking
> `expected_output.csv` still guards the result.

## The rules, serialized

As in chapter 01, the saved file *is* the mapping, and the same rule set
serializes to JSON (the default) or YAML — the extension decides which, and
both load identically. Shown in both formats below.

Worth noticing here is how a realistic, multi-rule mapping looks once written
out: every primitive this suite has covered — dates, units, text, lookups,
aggregation — sits side by side in one file, each rule carrying its own
operations and `metadata.rationale`. This is what a complete harmonization
looks like as a single reviewable artifact.

`rules.json`:

```json
[
  {
    "sources": [
      "patient_name"
    ],
    "target": "family_name",
    "operations": [
      {
        "operation": "substitute",
        "expression": "^\\s*([^,]+?)\\s*,.*$",
        "substitution": "\\1"
      },
      {
        "operation": "normalize_text",
        "normalization": "lower"
      }
    ],
    "metadata": {
      "rationale": "Extract surname (before comma), then lowercase to absorb inconsistent casing/whitespace across sites."
    }
  },
  {
    "sources": [
      "patient_name"
    ],
    "target": "given_name",
    "operations": [
      {
        "operation": "substitute",
        "expression": "^[^,]*,\\s*(.+?)\\s*$",
        "substitution": "\\1"
      },
      {
        "operation": "normalize_text",
        "normalization": "lower"
      }
    ],
    "metadata": {
      "rationale": "Extract given name (after comma), then lowercase; mirrors the family_name rule on the same source column."
    }
  },
  {
    "sources": [
      "visit_code"
    ],
    "target": "visit_type",
    "operations": [
      {
        "operation": "enum_to_enum",
        "mapping": [
          {
            "from": "BL",
            "to": "baseline"
          },
          {
            "from": "FU",
            "to": "follow_up"
          },
          {
            "from": "SC",
            "to": "screening"
          }
        ],
        "strict": false,
        "default": "unmapped"
      }
    ],
    "metadata": {
      "rationale": "Site codes drift; map the known set and surface anything else as 'unmapped' rather than failing the batch."
    }
  },
  {
    "sources": [
      "visit_date"
    ],
    "target": "visit_date_us",
    "operations": [
      {
        "operation": "convert_date",
        "source_format": "%Y-%m-%d",
        "target_format": "%m/%d/%Y"
      }
    ],
    "metadata": {
      "rationale": "Reformat to US display format. ConvertDate fails fast on malformed dates by design \u2014 preferable to a silent misparse for a clinically meaningful field."
    }
  },
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
      "rationale": "Convert at full precision, then round to 1 dp."
    }
  },
  {
    "sources": [
      "consent_research",
      "consent_biobank",
      "consent_none"
    ],
    "target": "consent_type",
    "operations": [
      {
        "operation": "reduce",
        "reduction": "one-hot"
      },
      {
        "operation": "enum_to_enum",
        "mapping": [
          {
            "from": 0,
            "to": "research"
          },
          {
            "from": 1,
            "to": "biobank"
          },
          {
            "from": 2,
            "to": "declined"
          }
        ],
        "strict": false,
        "default": "ambiguous"
      }
    ],
    "metadata": {
      "rationale": "Collapse 3 mutually-exclusive one-hot consent flags into one categorical; rows with zero/multiple flags become 'ambiguous' (one-hot -> None -> default) instead of a silently wrong label. Integer index keys EnumToEnum directly (serialized form preserves key type). Source order = index."
    }
  }
]
```

`rules.yaml`:

```yaml
- sources: [patient_name]
  target: family_name
  operations:
  - {operation: substitute, expression: '^\s*([^,]+?)\s*,.*$', substitution: \1}
  - {operation: normalize_text, normalization: lower}
  metadata: {rationale: 'Extract surname (before comma), then lowercase to absorb
      inconsistent casing/whitespace across sites.'}

- sources: [patient_name]
  target: given_name
  operations:
  - {operation: substitute, expression: '^[^,]*,\s*(.+?)\s*$', substitution: \1}
  - {operation: normalize_text, normalization: lower}
  metadata: {rationale: 'Extract given name (after comma), then lowercase; mirrors
      the family_name rule on the same source column.'}

- sources: [visit_code]
  target: visit_type
  operations:
  - operation: enum_to_enum
    mapping:
    - {from: BL, to: baseline}
    - {from: FU, to: follow_up}
    - {from: SC, to: screening}
    strict: false
    default: unmapped
  metadata: {rationale: Site codes drift; map the known set and surface anything else
      as 'unmapped' rather than failing the batch.}

- sources: [visit_date]
  target: visit_date_us
  operations:
  - {operation: convert_date, source_format: '%Y-%m-%d', target_format: '%m/%d/%Y'}
  metadata: {rationale: "Reformat to US display format. ConvertDate fails fast on\
      \ malformed dates by design \u2014 preferable to a silent misparse for a clinically\
      \ meaningful field."}

- sources: [height_in]
  target: height_cm
  operations:
  - {operation: convert_units, source_unit: inch, target_unit: cm}
  - {operation: round, precision: 1}
  metadata: {rationale: 'Convert at full precision, then round to 1 dp.'}

- sources: [consent_research, consent_biobank, consent_none]
  target: consent_type
  operations:
  - {operation: reduce, reduction: one-hot}
  - operation: enum_to_enum
    mapping:
    - {from: 0, to: research}
    - {from: 1, to: biobank}
    - {from: 2, to: declined}
    strict: false
    default: ambiguous
  metadata: {rationale: Collapse 3 mutually-exclusive one-hot consent flags into one
      categorical; rows with zero/multiple flags become 'ambiguous' (one-hot -> None
      -> default) instead of a silently wrong label. Integer index keys EnumToEnum
      directly (serialized form preserves key type). Source order = index.}
```

## Running it

```bash
../../../harmonization-framework/venv/bin/python build_rules.py
../../../harmonization-framework/venv/bin/python run_python.py   # run + assert
../../../harmonization-framework/venv/bin/python run_yaml.py     # same, from rules.yaml
bash run_cli.sh
```

## Expected output

`expected_output.csv` (Python API — all columns) ends with the harmonized
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

## Where to go from here

This was the last chapter. Across the guide you have seen the main families of
primitives at work:

- carrying a column across unchanged and renaming it, and mapping coded values
  to canonical labels (chapters 01, 05);
- numeric work — unit conversion, scaling, rounding, thresholds, and binning
  (chapter 02);
- text cleanup — substitution, normalisation, and truncation (chapter 03);
- date parsing, with the choice between failing and coercing (chapter 04);
- aggregating several source columns into one (chapter 06);
- and distinguishing genuine nulls from missing-value codes (chapter 07).

The recurring theme is that each rule is a decision, not just a transformation:
when to fail on bad input versus quietly fix it, when to keep a type stable, and
when to surface an anomaly rather than hide it. Every chapter records that
reasoning in each rule's `metadata`, so the rule set explains itself.

To go further, build a rule set of your own against a file you actually have:
start from the example closest to your problem, copy its `build_rules.py`, and
adapt the rules. The framework's own documentation lists the complete set of
primitives and their parameters.
