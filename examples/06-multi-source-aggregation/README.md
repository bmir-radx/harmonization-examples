# 06 — Multi-source Aggregation

Every rule so far has had a single source column. Often the value you want is
spread across several columns (three symptom flags that add up to a count, three
status flags that pick out one category) or packed into a single cell
(`"3|5|2"`). This example introduces rules that take *many* inputs and collapse
them to one output. The decision it teaches is choosing the right collapse:
summing co-occurring flags versus one-hot-decoding mutually exclusive ones. The
wrong reduction produces an incorrect value rather than an error, so the choice
matters.

## What it teaches

- **Collapsing many values with `reduce`.** N inputs → 1 output, via reductions
  `sum`, `any`, `none`, `all`, and `one-hot` (the index of the single set bit).
- **Choosing the right reduction.** Co-occurring flags call for `sum` (a count);
  mutually exclusive flags call for `one-hot` (a category) — the data's nature
  dictates the choice.
- **Unpacking a packed cell with `parse_array`.** Turn a delimited/JSON string
  into a list, then aggregate it.
- **Naming a one-hot index.** Feed the integer index straight into
  `enum_to_enum`; the integer keys round-trip safely (no cast needed).

## How multi-source rules work

The framework passes a **list** (one element per source, in `sources` order)
into the transformation; list-consuming primitives like `reduce` take it
directly. Two things to know:

- **Source order defines the one-hot index** — keep `sources` aligned with the
  downstream mapping keys.
- **`reduce` rejects nulls** — a null element raises an error rather than being
  silently dropped, because a missing source is a data-quality signal.
  Whole-column absence is handled separately by the CLI `--on-missing` policy
  (see Example 07).

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
malformed cell raises an error instead of yielding garbage.

## The rules, serialized

As in example 01, the saved file *is* the mapping, and the same rule set
serializes to JSON (the default) or YAML — the extension decides which, and
both load identically. Shown in both formats below.

Worth noticing here is how a multi-source rule is written out: the `sources`
list holds more than one column, and the `reduce` and `enum_to_enum` operations
chain in order, so the file records both which columns are combined and how the
combined index is turned into a label.

`rules.json`:

```json
[
  {
    "sources": [
      "sym_fever",
      "sym_cough",
      "sym_fatigue"
    ],
    "target": "symptom_count",
    "operations": [
      {
        "operation": "reduce",
        "reduction": "sum"
      }
    ],
    "metadata": {
      "rationale": "Independent (non-exclusive) symptom flags -> a count via SUM. ONE-HOT would be wrong: more than one can be set."
    }
  },
  {
    "sources": [
      "stat_new",
      "stat_active",
      "stat_closed"
    ],
    "target": "triage_status",
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
            "to": "new"
          },
          {
            "from": 1,
            "to": "active"
          },
          {
            "from": 2,
            "to": "closed"
          }
        ],
        "strict": false,
        "default": "ambiguous"
      }
    ],
    "metadata": {
      "rationale": "Mutually-exclusive status flags -> one label via ONE-HOT. Source order = index order. Zero/multiple set bits give None -> 'ambiguous'. The integer index feeds EnumToEnum directly \u2014 keys are kept as ints through serialization."
    }
  },
  {
    "sources": [
      "daily_scores"
    ],
    "target": "score_total",
    "operations": [
      {
        "operation": "parse_array",
        "format": "delimiter",
        "item_type": "integer",
        "strict": true,
        "allow_singleton": false,
        "delimiter": "|"
      },
      {
        "operation": "reduce",
        "reduction": "sum"
      }
    ],
    "metadata": {
      "rationale": "Packed multi-value cell: parse_array -> list of ints, then SUM. Demonstrates aggregation within one column."
    }
  }
]
```

`rules.yaml`:

```yaml
- sources: [sym_fever, sym_cough, sym_fatigue]
  target: symptom_count
  operations:
  - {operation: reduce, reduction: sum}
  metadata: {rationale: 'Independent (non-exclusive) symptom flags -> a count via
      SUM. ONE-HOT would be wrong: more than one can be set.'}

- sources: [stat_new, stat_active, stat_closed]
  target: triage_status
  operations:
  - {operation: reduce, reduction: one-hot}
  - operation: enum_to_enum
    mapping:
    - {from: 0, to: new}
    - {from: 1, to: active}
    - {from: 2, to: closed}
    strict: false
    default: ambiguous
  metadata: {rationale: "Mutually-exclusive status flags -> one label via ONE-HOT.\
      \ Source order = index order. Zero/multiple set bits give None -> 'ambiguous'.\
      \ The integer index feeds EnumToEnum directly \u2014 keys are kept as ints through\
      \ serialization."}

- sources: [daily_scores]
  target: score_total
  operations:
  - {operation: parse_array, format: delimiter, item_type: integer, strict: true,
    allow_singleton: false, delimiter: '|'}
  - {operation: reduce, reduction: sum}
  metadata: {rationale: 'Packed multi-value cell: parse_array -> list of ints, then
      SUM. Demonstrates aggregation within one column.'}
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
...,symptom_count,triage_status,score_total,...
K1,...,2,new,10,...
K2,...,0,active,14,...
K3,...,2,closed,20,...
K4,...,2,active,9,...
```
