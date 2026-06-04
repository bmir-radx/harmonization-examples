# 06 — Multi-source Aggregation

Rules whose `sources` list has **more than one column**, collapsing several
inputs into one target — plus aggregating many values packed into one column.

## What it teaches

- `reduce` — N inputs → 1 output. Reductions: `sum`, `any`, `none`, `all`,
  `one-hot` (index of the single set bit).
- `parse_array` — parse a packed cell (delimited/JSON) into a list.
- Feeding a one-hot integer index straight into `enum_to_enum` to name it —
  the integer keys round-trip safely (no cast needed).

## How multi-source rules work

The framework passes a **list** (one element per source, in `sources` order)
into the transformation; list-consuming primitives like `reduce` take it
directly. Two things to know:

- **Source order defines the one-hot index** — keep `sources` aligned with the
  downstream mapping keys.
- **`reduce` rejects nulls** — a null element raises rather than being silently
  dropped, because a missing source is a data-quality signal. Whole-column
  absence is handled separately by the CLI `--on-missing` policy.

## The data

`input.csv`:

| case_id | sym_fever | sym_cough | sym_fatigue | stat_new | stat_active | stat_closed | daily_scores |
|---------|-----------|-----------|-------------|----------|-------------|-------------|--------------|
| K1 | 1 | 1 | 0 | 1 | 0 | 0 | `3\|5\|2` |
| K2 | 0 | 0 | 0 | 0 | 1 | 0 | `7\|7` |
| K3 | 1 | 0 | 1 | 0 | 0 | 1 | `4\|6\|5\|5` |
| K4 | 0 | 1 | 1 | 0 | 1 | 0 | `9` |

## The harmonization choices (and why)

| Sources | Target | Pipeline | Why |
|---------|--------|----------|-----|
| 3 `sym_*` flags | `symptom_count` | `reduce(sum)` | Independent (non-exclusive) flags → a count. `sum`, not `one-hot`, because more than one can be set. |
| 3 `stat_*` flags | `triage_status` | `reduce(one-hot)` → `enum_to_enum` (int keys) | Mutually exclusive flags → one label. Index 0/1/2 → `new`/`active`/`closed`. Zero/multiple bits → `None` → `ambiguous`. |
| `daily_scores` (one column) | `score_total` | `parse_array(\|, int)` → `reduce(sum)` | A single packed cell parsed to a list, then summed. |

### sum vs. one-hot

`symptom_count` and `triage_status` both reduce three flag columns, but the
*nature* of the flags dictates the reduction. Symptoms co-occur → `sum` gives a
count. Status is exclusive → `one-hot` gives a category. Picking the wrong one
silently produces nonsense (e.g. `one-hot` on co-occurring symptoms returns
`None` whenever ≥2 are set).

### Aggregating within one column

`score_total` is a **single-source** rule, so the transformation receives the
scalar string (`"3|5|2"`). `parse_array` turns it into `[3, 5, 2]`, then
`reduce(sum)` collapses it to `10`. `parse_array` is strict by default, so a
malformed cell raises instead of yielding garbage.

## Running it

```bash
../../../harmonization-framework/venv/bin/python build_rules.py
../../../harmonization-framework/venv/bin/python run_python.py
bash run_cli.sh
```

## Expected output

```
...,symptom_count,triage_status,score_total,...
K1,...,2,new,10,...
K2,...,0,active,14,...
K3,...,2,closed,20,...
K4,...,2,active,9,...
```
