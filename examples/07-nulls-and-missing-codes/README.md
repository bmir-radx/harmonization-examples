# 07 — Nulls & Missing-Value Codes

Most real datasets have some missing values, but a CSV has no built-in way to
say "this value is missing." The closest it has is an **empty field** — nothing
between two commas (`...,neg,,160.0,...`). When Python's pandas reads the file,
an empty field in *any* column — text or numeric — is parsed as a missing
value, which pandas represents with the marker `NaN` ("Not a Number," the
floating-point value pandas reuses as its general "missing" marker for every
column type, not just numbers). Turning the empty field into `NaN` is pandas'
doing, not the harmonization framework's. But `NaN` is a real null — one of a
few equivalent "missing" values the harmonization framework recognises (`NaN`,
Python's own `None`, and pandas' `pd.NA`; see *Verified null semantics* below) —
and it quietly protects them: its scalar transforms are wrapped so that a null is
returned as-is instead of being fed through the transform. The two layers
together mean a blank cell in produces a blank cell out with no effort on your
part.

The catch is that not every "missing" value arrives as an empty field. Source
systems often fill the gap with a *missing-value code* instead — an in-band
value like `UNK` in a text column or `-999` in a numeric one. To a person these
read as "we don't have this," but to pandas they are perfectly ordinary strings
and numbers. They are *not* nulls, nothing protects them, and they flow through
every transform and quietly corrupt the result. For example, a `-999` "missing"
code in a pounds column scales right through a pounds-to-kilograms conversion
and ends up in the output as `-453.14 kg` — a real-looking number that is pure
garbage. A `UNK` in a category column survives a rename/standardisation step and
shows up as its own bogus category, so a count of distinct results reports one
too many. In both cases nothing errors out; the pipeline produces a clean,
plausible answer that happens to be wrong. This example walks through both
— how the harmonization framework handles real nulls for you, and what you have to do yourself
about missing-value codes — using a small dataset that deliberately mixes the two.

## What it teaches

- **Real null semantics.** Genuine nulls (`None`, `NaN`, blank cells) are
  understood by the harmonization framework and **pass through** scalar transforms unchanged,
  so you almost never have to think about them.
- **Missing-value codes are not nulls.** Values like `UNK` and `-999` look like
  "missing" to a person but are ordinary data to the harmonization framework.
  They will corrupt results unless you handle them explicitly — a categorical
  code folds into `enum_to_enum`, and a numeric code is turned into a real null
  by the `missing_code` primitive, which also reports each nulled cell to the
  replay log.
- **Missing columns are a different problem.** The CLI's `--on-missing` policy
  governs whole *columns* that are absent from the input, which is a separate
  concern from the value-level handling above. This example shows both so you
  don't conflate them.

## How the framework treats a real null

A genuine null is any of three specific values — Python's `None`,
floating-point `NaN`, or pandas' `pd.NA` — and the harmonization framework gives
all three the same guarantee: when one reaches a scalar transform (`scale`,
`round`, `cast`, …), the transform is skipped and the null is returned
unchanged. So for a rule built only from scalar transforms, a missing input
produces a missing output and you write no extra handling. The one place this
guarantee does *not* hold is the aggregating primitives `reduce` and `map_each`,
which raise on a missing element rather than passing it through. The three rules
below state each part exactly:

**A null is one of three things.** When the framework asks "is this value
missing?", it answers yes for exactly three forms: Python's `None`, the
floating-point `NaN` (what a blank CSV cell becomes), and pandas' `pd.NA`. The
check works on single values only — a *scalar* — not on whole lists or arrays.

**Most transforms pass a null straight through.** Scalar primitives such as
`scale`, `round`, and `cast` are written so that a null skips the transform
entirely and comes out unchanged. So a blank cell stays blank all the way to the
output — multiply-by-ten leaves it blank, rounding leaves it blank, and so on.
This is why the `score_x10` rule later needs no special handling for its empty
cells: the framework already does the right thing.

**Aggregations are the exception — they refuse to guess.** The list-consuming
primitives `reduce` and `map_each` do *not* quietly skip a missing element;
they raise an error instead. The reasoning is that a hole in the middle of a
sum or an average is a data-quality problem you should know about, not something
to paper over with a silent partial result. (Example 06 explores this in
depth.)

## The data

`input.csv` is built to contain all three flavours of "missing" at once: a
categorical missing-value code (`UNK`), genuine blank cells, and a numeric
missing-value code (`-999`). That lets a single run show how each is treated.

| sample_id | result | score | reading_lb |
|-----------|--------|-------|-----------|
| N1 | pos | 12.5 | 150.0 |
| N2 | neg | *(blank)* | 160.0 |
| N3 | **UNK** | 8.0 | **-999** |
| N4 | pos | *(blank)* | 175.5 |

Row `N3` is the interesting one: its `result` is the categorical code `UNK`,
and its `reading_lb` is the numeric code `-999`. Rows `N2` and `N4` have
genuinely blank `score` cells, which is the easy, well-behaved case.

## The harmonization choices (and why)

The example defines three rules, one per source column. Read together they show
the full range of effort missing data demands — from "the framework handles it
for you" through "you handle it with the tools you have" to "no in-pipeline tool
can handle it." Here they are at a glance, then walked one at a time:

| Source | Target | Pipeline | What happens to the missing entry |
|--------|--------|----------|-----------|
| `score` | `score_x10` | `scale(10)` | The blank cells (N2, N4) are real nulls, so `scale` skips them and they stay blank. |
| `result` | `result_clean` | `enum_to_enum({pos,neg,UNK→null}, default="unexpected")` | `UNK` is mapped to null alongside the real vocabulary, so it becomes blank; an unmapped surprise becomes `unexpected`. |
| `reading_lb` | `reading_kg` | `missing_code({-999: "not_measured"})` → `scale(0.45359237)` | `missing_code` turns `-999` into a real null (and reports it to the replay log); `scale` then passes the null through, so `reading_kg` is blank for N3. |

**Start with `score_x10`, the case that needs nothing.** Its `score` column has
genuinely blank cells in rows N2 and N4, which arrive as real nulls. By the rule
from the previous section, `scale` skips a null and returns it unchanged, so the
blanks stay blank in `score_x10` with no extra work. This rule is in the example
only to show the baseline: when "missing" is a true null, you write the
transform you'd write anyway and the framework does the right thing.

**`result_clean` and `reading_kg` are where the work is**, because both columns
carry a missing-value *code* — `UNK` in the text column and `-999` in the
numeric one — and neither code is a null. Each calls for a different approach,
and those two approaches are the heart of this example, covered next.

### Missing-value code → null: the two patterns

**Pattern A — categorical, known vocabulary (solvable in the pipeline).** When the column
draws from a small, known set of values, you can fold the missing-value code
into the same `enum_to_enum` that canonicalises the real values: map every
legitimate value *and* the code, sending the code to `None`. Because every
legitimate value is explicitly mapped, the `default` never fires for ordinary
data — it only catches genuine surprises, which is exactly what you want it to
flag:

```
pos → positive,  neg → negative,  UNK → null,  (xyz → "unexpected")
```

Here `UNK` becomes a real null (a blank output cell), `pos`/`neg` become their
canonical labels, and anything unexpected (say `xyz`) surfaces as
`"unexpected"` rather than being silently swallowed.

**Pattern B — numeric code, handled with `missing_code`.** A numeric column
can't use Pattern A: `enum_to_enum` has no "pass through unchanged" branch — an
unmapped value always returns the `default` — so `{-999: None}` with
`default=None` would null *every* reading, not just the code, and you can't
identity-map every legitimate value of a continuous measurement. The
`missing_code` primitive exists for exactly this case. It is the
identity-preserving null map `enum_to_enum` lacks. In `rules.json` it serializes
as a list of `{"code", "label"}` entries — an entry-list, not a JSON object, so
the numeric code keeps its type through a round-trip (the same reason
`enum_to_enum` uses `{"from","to"}` entries; see example 05):

```
"codes": [{"code": -999, "label": "not_measured"}]
  -999  → null        (the declared code becomes a real null)
  150.0 → 150.0       (every other value passes through unchanged)
```

Each code is paired with a label describing what it means
(`"not_measured"`). The label is **not** written into the output column — a null
has no room for a reason — but the harmonize engine reports every nulled cell,
with its label and row, to the **replay log**:

```
{"event": "missing_code", "target": "reading_kg", "source": "reading_lb",
 "row": 2, "value": -999.0, "label": "not_measured"}
```

So the distinction between different codes (`-999` = not measured vs, say, `-1` =
refused) is preserved in the audit trail without cluttering the output. In the
rule, `missing_code` runs **first**, on the raw `reading_lb` value: it turns
`-999` into a null, and because `scale` passes nulls through unchanged, the null
flows straight to a blank `reading_kg` for N3. No corruption, and the
codes and their meanings are declared right in `rules.json`.

## Missing columns vs. missing values

So far everything has been about missing *values* inside columns that exist.
A separate question is what happens when an entire *column* is absent from the
input. That is governed by the CLI's `--on-missing` policy, and it is
completely independent of the value-level null handling above. To see it,
imagine running with the `score` column removed from the input:

```bash
# Fails fast — the score_x10 rule's source column is gone:
... cli --on-missing error   # -> "Missing source columns: score"

# Skips that one rule and harmonizes the rest:
... cli --on-missing warn     # -> "Warning: skipping missing source columns: score"
```

Use `error` when a missing column means the input is malformed and you'd rather
stop than produce a partial result; use `warn` when sources legitimately vary
and you want the rest of the harmonization to proceed regardless.

## The rules, serialized

The full rule set for this example, in both formats. `RuleSet.save()` and `load()` (and the CLI's `--rules`) pick the format from the file extension (`.yaml`/`.yml` for YAML, otherwise JSON), and both load identically.

`rules.json`:

```json
[
  {
    "sources": [
      "result"
    ],
    "target": "result_clean",
    "operations": [
      {
        "operation": "enum_to_enum",
        "mapping": [
          {
            "from": "pos",
            "to": "positive"
          },
          {
            "from": "neg",
            "to": "negative"
          },
          {
            "from": "UNK",
            "to": null
          }
        ],
        "strict": false,
        "default": "unexpected"
      }
    ],
    "metadata": {
      "rationale": "Missing-value code 'UNK' -> null by mapping it explicitly alongside the real vocabulary; default flags only truly unexpected codes. (No null_if primitive exists.)"
    }
  },
  {
    "sources": [
      "score"
    ],
    "target": "score_x10",
    "operations": [
      {
        "operation": "scale",
        "scaling_factor": 10
      }
    ],
    "metadata": {
      "rationale": "Genuine NaN passes through @handle_null unchanged; a blank input cell yields a blank output cell."
    }
  },
  {
    "sources": [
      "reading_lb"
    ],
    "target": "reading_kg",
    "operations": [
      {
        "operation": "missing_code",
        "codes": [
          {
            "code": -999,
            "label": "not_measured"
          }
        ]
      },
      {
        "operation": "scale",
        "scaling_factor": 0.45359237
      }
    ],
    "metadata": {
      "rationale": "Numeric missing-value code -999 -> null via missing_code (identity-preserving: other readings pass through), then Scale passes the null through. The label is reported to the replay log."
    }
  }
]
```

`rules.yaml`:

```yaml
- sources: [result]
  target: result_clean
  operations:
  - operation: enum_to_enum
    mapping:
    - {from: pos, to: positive}
    - {from: neg, to: negative}
    - {from: UNK, to: null}
    strict: false
    default: unexpected
  metadata: {rationale: Missing-value code 'UNK' -> null by mapping it explicitly
      alongside the real vocabulary; default flags only truly unexpected codes. (No
      null_if primitive exists.)}

- sources: [score]
  target: score_x10
  operations:
  - {operation: scale, scaling_factor: 10}
  metadata: {rationale: Genuine NaN passes through @handle_null unchanged; a blank
      input cell yields a blank output cell.}

- sources: [reading_lb]
  target: reading_kg
  operations:
  - operation: missing_code
    codes:
    - {code: -999, label: not_measured}
  - {operation: scale, scaling_factor: 0.45359237}
  metadata: {rationale: 'Numeric missing-value code -999 -> null via missing_code
      (identity-preserving: other readings pass through), then Scale passes the null
      through. The label is reported to the replay log.'}
```

## Running it

Run any variant — they all consume the same rules, so the results match:

```bash
# Rebuild rules.json AND rules.yaml from build_rules.py:
../../../harmonization-framework/venv/bin/python build_rules.py

# Python API — also runs the golden self-check against expected_output.csv:
../../../harmonization-framework/venv/bin/python run_python.py

# Same, loading rules.yaml instead of rules.json:
../../../harmonization-framework/venv/bin/python run_yaml.py

# CLI variant:
bash run_cli.sh
```

## Expected output

The annotated golden master below shows each case landing where the table
predicted: `UNK` blanked out, real blanks staying blank, and the numeric code
`-999` turned into a clean blank `reading_kg` (with the hit recorded in the
replay log) rather than a corrupted `-453.14`.

```
sample_id,result,score,reading_lb,result_clean,score_x10,reading_kg,...
N1,pos,12.5,150.0,positive,125.0,68.0388555,...
N2,neg,,160.0,negative,,72.5747792...,...
N3,UNK,8.0,-999.0,,80.0,,...                  <- -999 nulled by missing_code; reading_kg blank
N4,pos,,175.5,positive,,79.6054609...,...
```
