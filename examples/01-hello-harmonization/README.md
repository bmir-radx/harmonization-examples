# 01 — Hello Harmonization

This is the first example. It introduces the framework's core model: two
source columns are mapped to two target columns, run both through the Python
API and the command-line tool. Later examples build on the pieces introduced
here.

The model is small. You describe a mapping as a set of **rules**. Each rule
takes one or more **source** columns and produces a single **target** column by
running the source value through an ordered list of **primitive operations** —
small, named transformations like "look this code up in a table" or "carry it
across unchanged." A collection of rules is a **RuleSet**, which you build in
Python and save to a file called `rules.json`. You define the rules once there;
both the Python API and the command-line tool read that same `rules.json`, so
the mapping runs identically through either.

## What it teaches

- **The rule model.** A rule maps source column(s) → one target column through
  an ordered list of primitive operations. This is the unit you compose
  everything else from.
- **Two foundational primitives.** `do_nothing` carries a column across
  unchanged (effectively a rename), and `enum_to_enum` looks source codes up in
  a table to produce target labels.
- **The rules file drives both interfaces.** A `RuleSet` saved to `rules.json`
  is read unchanged by both the Python API and the CLI, so you write the rules
  once and both run the same thing.

## The data

`input.csv` is a tiny participant roster with a clean name column and a coded
status column:

| participant_id | full_name | status_code |
|----------------|-----------|-------------|
| P001 | Ada Lovelace | A |
| P002 | Alan Turing | I |
| P003 | Grace Hopper | P |
| P004 | Katherine Johnson | A |

We want two harmonized columns out of it: a `name` (the same value, under the
canonical column name) and a `status` (the single-letter code expanded to a
readable label).

## The harmonization choices (and why)

| Source | Target | Operations | Why this choice |
|--------|--------|-----------|-----------------|
| `full_name` | `name` | `do_nothing` | The source is already clean; we only want it under the canonical column name. |
| `status_code` | `status` | `enum_to_enum` | Expand controlled codes to readable labels, with a visible fallback for anything unexpected. |

### Rule 1 — carry a column across unchanged

`full_name` already holds exactly the value we want; it just needs to land in a
target column called `name`. The `do_nothing` primitive expresses precisely
that: "carry this across, no transformation." You could express the same thing
with an empty list of operations, but a `do_nothing` says the intent out loud —
*this column is deliberately passed through* — and shows up as a visible
operation in `rules.json` rather than an absence someone might mistake for an
oversight.

### Rule 2 — map codes to labels

`status_code` uses single-letter codes (`A`/`I`/`P`) that the target schema
wants as full words. `enum_to_enum` is a lookup table: it maps each known code
to its label (`A → active`, `I → inactive`, `P → pending`). The interesting
decision is what happens to a code that *isn't* in the table. Two behaviours are
available:

- **Strict** — raise an error on any unknown code. Fail fast; good when the code
  set is guaranteed and a surprise should halt the run.
- **Lenient + default** — map unknown codes to a chosen fallback value and keep
  going.

This example chooses **lenient** with `default="unknown"`. Real intake data
drifts — a new status code shows up that nobody warned you about — and we'd
rather surface that as a *visible* `"unknown"` than crash the whole batch or
emit a blank cell that could mean several things. (Example 05 explores the
strict-vs-lenient trade-off in depth.)

The reasoning for each rule is also recorded in its `metadata.rationale`, so it
survives into `rules.json` and travels with the rule.

## The rules, serialized

A `RuleSet` is not only something you build in Python — it is saved to a file,
and that file *is* the mapping. It is what the Python API reloads, what the CLI
reads, and what you would commit, review, or hand to someone else. So it is
worth seeing what the rules you wrote above actually look like once written
out, because this file — not the Python that produced it — is the portable,
shareable artifact.

The same rule set serializes to two formats. JSON is the default; YAML is
offered because it is easier to read and edit by hand. `RuleSet.save()` and
`load()` (and the CLI's `--rules`) pick the format from the file extension
(`.yaml`/`.yml` for YAML, otherwise JSON), and both load to exactly the same
rules — the choice is purely about which you would rather look at.

Reading either one back, you can see the structure described above made
concrete: a list of rules, each with its `sources`, `target`, ordered
`operations`, and the `metadata.rationale` carried along. The `enum_to_enum`
lookup table, the `strict: false` / `default: unknown` choice — every decision
from the section above is right there in the file.

`rules.json`:

```json
[
  {
    "sources": [
      "full_name"
    ],
    "target": "name",
    "operations": [
      {
        "operation": "do_nothing"
      }
    ],
    "metadata": {
      "rationale": "Source is already clean; carry it across under the canonical column name with no transformation."
    }
  },
  {
    "sources": [
      "status_code"
    ],
    "target": "status",
    "operations": [
      {
        "operation": "enum_to_enum",
        "mapping": [
          {
            "from": "A",
            "to": "active"
          },
          {
            "from": "I",
            "to": "inactive"
          },
          {
            "from": "P",
            "to": "pending"
          }
        ],
        "strict": false,
        "default": "unknown"
      }
    ],
    "metadata": {
      "rationale": "Codes are controlled but data entry is imperfect; map known codes and surface anything unexpected as 'unknown' rather than failing the batch or emitting a blank."
    }
  }
]
```

`rules.yaml`:

```yaml
- sources: [full_name]
  target: name
  operations:
  - {operation: do_nothing}
  metadata: {rationale: Source is already clean; carry it across under the canonical
      column name with no transformation.}

- sources: [status_code]
  target: status
  operations:
  - operation: enum_to_enum
    mapping:
    - {from: A, to: active}
    - {from: I, to: inactive}
    - {from: P, to: pending}
    strict: false
    default: unknown
  metadata: {rationale: Codes are controlled but data entry is imperfect; map known
      codes and surface anything unexpected as 'unknown' rather than failing the batch
      or emitting a blank.}
```

## Running it

`build_rules.py` is the only place the rules are defined. Running it writes both
`rules.json` and `rules.yaml`, and the other interfaces read those files:

```bash
# 0. (Re)generate rules.json AND rules.yaml from build_rules.py:
../../../harmonization-framework/venv/bin/python build_rules.py

# 1. Python API — harmonizes and checks the result against expected_output.csv:
../../../harmonization-framework/venv/bin/python run_python.py

# 2. Same, but loading the YAML rules instead — same output:
../../../harmonization-framework/venv/bin/python run_yaml.py

# 3. CLI — no Python needed (accepts rules.json or rules.yaml):
bash run_cli.sh
```

Because they all read the same rules, the mapping behaves the same way whichever
you use. There is one intentional difference in *output shape*: the
Python API returns every input column plus the new targets, while the CLI
returns only the target columns (add `--include-metadata` to also get the
`source dataset` / `original_id` columns). Same rules, same values — the
interfaces just differ in how much of the input they echo back.

## Expected output

The Python API produces the full output — all input columns, the two new
targets, and metadata:

```
participant_id,full_name,status_code,name,status,source dataset,original_id
P001,Ada Lovelace,A,Ada Lovelace,active,hello,0
P002,Alan Turing,I,Alan Turing,inactive,hello,1
P003,Grace Hopper,P,Grace Hopper,pending,hello,2
P004,Katherine Johnson,A,Katherine Johnson,active,hello,3
```

The CLI emits only the targets (plus metadata when `--include-metadata` is
passed):

```
name,status,source dataset,original_id
Ada Lovelace,active,hello,0
Alan Turing,inactive,hello,1
Grace Hopper,pending,hello,2
Katherine Johnson,active,hello,3
```

`run_python.py` asserts its output against the committed `expected_output.csv`,
so the example checks itself.

## Generated files (not committed)

`output.csv`, `output_cli.csv`, and `replay.log` are produced when you run the
example. The committed artifacts are `input.csv`, `rules.json`, and
`expected_output.csv`.
