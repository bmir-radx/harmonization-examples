# 03 — Text & Names

Free-text fields often need several cleanups at once: a name might carry a
leading honorific, irregular internal spacing, trailing whitespace, accents, or
a `"Last, First"` ordering. Cleaning them is a matter of applying small string
transforms in the right *sequence*, because a step that depends on the original
structure (a regex anchored on a capital letter, say) must run before a step
that changes that structure (lowercasing). This example cleans a set of untidy
names and shows the ordering that keeps text transforms from undoing each
other.

## What it teaches

- **Extracting and replacing with `substitute`.** A regex extract/replace —
  here used to drop honorifics and collapse runs of whitespace.
- **Normalising with `normalize_text`.** `strip`, `upper`, and `remove_accents`
  (NFKD folding, so `José` → `Jose`, `ÅSA` → `ASA`, `Síle` → `Sile`).
- **Capping length with `truncate`.** Cut a string to a fixed length.
- **The recurring discipline.** Clean the *structure* first with `substitute`,
  then `normalize` the result — not the other way around.

## The data

`input.csv` has names with leading honorifics, irregular internal whitespace,
trailing spaces, accents, and one `"Last, First"` entry:

| contact_id | raw_name | country |
|------------|----------|---------|
| C1 | `Dr. José  Ortega ` | Spain |
| C2 | `  ms. ÅSA Lindqvist` | Sweden |
| C3 | `Jean-Luc   Picard` | France |
| C4 | `O'Brien, Síle` | Ireland |

## The harmonization choices (and why)

| Source | Target | Pipeline | Why |
|--------|--------|----------|-----|
| `raw_name` | `display_name` | `substitute(drop honorific)` → `substitute(collapse \s+)` → `normalize_text(strip)` | Strip the honorific while it's still anchored at `^`; collapse runs of whitespace; trim ends. |
| `raw_name` | `name_ascii` | …same three… → `normalize_text(remove_accents)` | An ASCII-folded variant for case-insensitive matching/joining. Fold accents **last**, on already-clean text. |
| `country` | `country_code` | `truncate(2)` → `normalize_text(upper)` | Demonstrates `truncate`. **Deliberately crude** (Spain → `SP`, not ISO `ES`). |

### Why extract-then-normalize

If you lowercased/normalized the whole field first, a regex anchored on a
capitalized honorific or on leading whitespace could stop matching. Define the
structure with `substitute` while the original text is intact, then normalize
the cleaned result.

### A teaching anti-example

`country_code` uses `truncate` to fake a country code. That's the *wrong* tool
for an authoritative code system — `SW` for Sweden isn't ISO-3166 (`SE`).
Authoritative code mapping belongs in an `enum_to_enum` lookup (example 05).
The example includes this on purpose so the contrast is explicit.

## The rules, serialized

As in example 01, the saved file *is* the mapping, and the same rule set
serializes to JSON (the default) or YAML — the extension decides which, and
both load identically. Shown in both formats below.

Worth noticing here is how the text primitives chain: `normalize_text`,
`substitute`, and `truncate` appear as an ordered list of operations on a
single rule, each with its own parameters, so the file records both the
sequence and the exact settings (which substitutions, what length limit).

`rules.json`:

```json
[
  {
    "sources": [
      "raw_name"
    ],
    "target": "display_name",
    "operations": [
      {
        "operation": "substitute",
        "expression": "(?i)^\\s*(dr|mr|mrs|ms|prof)\\.?\\s+",
        "substitution": ""
      },
      {
        "operation": "substitute",
        "expression": "\\s+",
        "substitution": " "
      },
      {
        "operation": "normalize_text",
        "normalization": "strip"
      }
    ],
    "metadata": {
      "rationale": "Strip honorific prefix, collapse internal whitespace, trim ends. Substitutions run before the strip so the regex anchors (^) still see the original leading text."
    }
  },
  {
    "sources": [
      "raw_name"
    ],
    "target": "name_ascii",
    "operations": [
      {
        "operation": "substitute",
        "expression": "(?i)^\\s*(dr|mr|mrs|ms|prof)\\.?\\s+",
        "substitution": ""
      },
      {
        "operation": "substitute",
        "expression": "\\s+",
        "substitution": " "
      },
      {
        "operation": "normalize_text",
        "normalization": "strip"
      },
      {
        "operation": "normalize_text",
        "normalization": "remove_accents"
      }
    ],
    "metadata": {
      "rationale": "ASCII-folded variant for matching/joining. Accent removal (NFKD) runs last, on already-cleaned text."
    }
  },
  {
    "sources": [
      "country"
    ],
    "target": "country_code",
    "operations": [
      {
        "operation": "truncate",
        "length": 2
      },
      {
        "operation": "normalize_text",
        "normalization": "upper"
      }
    ],
    "metadata": {
      "rationale": "Crude 2-letter code via truncate+upper to demonstrate truncate. For authoritative codes use an enum_to_enum lookup instead (see example 05)."
    }
  }
]
```

`rules.yaml`:

```yaml
- sources: [raw_name]
  target: display_name
  operations:
  - {operation: substitute, expression: '(?i)^\s*(dr|mr|mrs|ms|prof)\.?\s+', substitution: ''}
  - {operation: substitute, expression: \s+, substitution: ' '}
  - {operation: normalize_text, normalization: strip}
  metadata: {rationale: 'Strip honorific prefix, collapse internal whitespace, trim
      ends. Substitutions run before the strip so the regex anchors (^) still see
      the original leading text.'}

- sources: [raw_name]
  target: name_ascii
  operations:
  - {operation: substitute, expression: '(?i)^\s*(dr|mr|mrs|ms|prof)\.?\s+', substitution: ''}
  - {operation: substitute, expression: \s+, substitution: ' '}
  - {operation: normalize_text, normalization: strip}
  - {operation: normalize_text, normalization: remove_accents}
  metadata: {rationale: 'ASCII-folded variant for matching/joining. Accent removal
      (NFKD) runs last, on already-cleaned text.'}

- sources: [country]
  target: country_code
  operations:
  - {operation: truncate, length: 2}
  - {operation: normalize_text, normalization: upper}
  metadata: {rationale: Crude 2-letter code via truncate+upper to demonstrate truncate.
      For authoritative codes use an enum_to_enum lookup instead (see example 05).}
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
contact_id,raw_name,country,display_name,name_ascii,country_code,...
C1,Dr. José  Ortega ,Spain,José Ortega,Jose Ortega,SP,...
C2,  ms. ÅSA Lindqvist,Sweden,ÅSA Lindqvist,ASA Lindqvist,SW,...
```

`display_name` keeps accents; `name_ascii` folds them. The CLI emits only the
target columns (+ metadata with `--include-metadata`).
