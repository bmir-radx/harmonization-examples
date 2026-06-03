# 03 — Text & Names

Cleaning and reshaping free-text fields — the most error-prone part of most
harmonizations.

## What it teaches

- `substitute` — regex extract/replace (drop honorifics, collapse whitespace).
- `normalize_text` — `strip`, `upper`, `remove_accents` (NFKD folding, so
  `José` → `Jose`, `ÅSA` → `ASA`, `Síle` → `Sile`).
- `truncate` — cap a string to a fixed length.
- The recurring rule: **substitute/clean structure first, normalize second.**

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

## Running it

```bash
../../../harmonization-framework/venv/bin/python build_rules.py
../../../harmonization-framework/venv/bin/python run_python.py
bash run_cli.sh
node client.ts   # start the sidecar first
```

## Expected output

```
contact_id,raw_name,country,display_name,name_ascii,country_code,...
C1,Dr. José  Ortega ,Spain,José Ortega,Jose Ortega,SP,...
C2,  ms. ÅSA Lindqvist,Sweden,ÅSA Lindqvist,ASA Lindqvist,SW,...
```

`display_name` keeps accents; `name_ascii` folds them. The CLI emits only the
target columns (+ metadata with `--include-metadata`).
