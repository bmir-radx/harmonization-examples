# 01 — Hello Harmonization

The smallest complete harmonization. Start here.

## What it teaches

- A **rule** maps source column(s) → one target column via an ordered list of
  **primitive operations**.
- A **RuleSet** is a collection of rules you build in Python and `save()` to
  JSON; the CLI and sidecar then consume that JSON.
- Two foundational primitives:
  - `DoNothing` — carry a column across unchanged (effectively a rename).
  - `EnumToEnum` — a lookup table from source codes to target labels.

## The data

`input.csv`:

| participant_id | full_name | status_code |
|----------------|-----------|-------------|
| P001 | Ada Lovelace | A |
| P002 | Alan Turing | I |
| P003 | Grace Hopper | P |
| P004 | Katherine Johnson | A |

## The harmonization choices (and why)

| Target | Source | Operations | Why this choice |
|--------|--------|-----------|-----------------|
| `name` | `full_name` | `do_nothing` | The source is already clean. We only want the canonical column name, so a no-op transformation documents "carry across, no change" explicitly. |
| `status` | `status_code` | `enum_to_enum` | Codes are controlled but data entry is imperfect. We use `strict=False` with `default="unknown"` so an unexpected code maps to a *visible* `"unknown"` rather than crashing the batch or leaving an ambiguous blank cell. |

The reasoning is also recorded in each rule's `metadata.rationale`, so it
survives into `rules.json` and travels with the rule.

> **Design note — strict vs. lenient mapping.** `strict=True` would raise on an
> unknown code (fail fast, good when codes are guaranteed). We chose lenient +
> explicit default here because real intake data drifts. Example 05 explores
> this trade-off directly.

## Running it (three interfaces, one source of truth)

```bash
# 0. (Re)generate rules.json from the Python source of truth:
../../../harmonization-framework/venv/bin/python build_rules.py

# 1. Python API — harmonizes and asserts against expected_output.csv:
../../../harmonization-framework/venv/bin/python run_python.py

# 2. CLI — same rules.json, target columns only:
bash run_cli.sh

# 3. RPC sidecar — start the sidecar, then:
node client.ts
```

## Expected output

`expected_output.csv` (produced by the **Python API** and the **sidecar** — all
input columns plus the targets plus metadata):

```
participant_id,full_name,status_code,name,status,source dataset,original_id
P001,Ada Lovelace,A,Ada Lovelace,active,hello,0
...
```

The **CLI** instead emits only the target columns (`name`, `status`), plus
`source dataset`/`original_id` when `--include-metadata` is passed:

```
name,status,source dataset,original_id
Ada Lovelace,active,hello,0
...
```

This column-set difference between interfaces is intentional in the framework.

## Generated files (not committed)

`output.csv`, `output_cli.csv`, `output_rpc.csv`, `replay.log` are produced when
you run the example. The committed artifacts are `input.csv`, `rules.json`, and
`expected_output.csv`.
