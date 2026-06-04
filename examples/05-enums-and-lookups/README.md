# 05 — Enums & Lookups

Much of harmonization is translation: a source uses codes (`A`, `5`, `web`) and
the target schema wants labels (`active`, `very_satisfied`, `digital`). The
`enum_to_enum` primitive is the lookup table that does this. The decision
attached to it is what should happen to a value that *isn't* in the table. This
example maps three survey columns and applies that decision both ways — using
one column strict and lenient — so the trade-off is visible side by side.

## What it teaches

- **Lookups with `enum_to_enum`.** The core code → label primitive.
- **Strict vs. lenient, side by side.** `strict=True` (raise on an unknown code)
  versus `strict=False` + a `default` (coerce and keep going) — both applied to
  the same column so the contrast is concrete.
- **Type coercion with `cast`.** A true binary (`0`/`1`) becomes a native
  boolean without a lookup table.
- **Integer-keyed maps round-trip safely.** You can key a map by integers and
  map them to string labels with no special handling.

## The data

`input.csv` — survey responses:

| response_id | satisfaction | recommend | channel |
|-------------|-------------|-----------|---------|
| R1 | 5 | 1 | web |
| R2 | 3 | 0 | phone |
| R3 | 1 | 1 | web |
| R4 | 4 | 0 | kiosk |

## The harmonization choices (and why)

| Source | Target | Pipeline | Why |
|--------|--------|----------|-----|
| `satisfaction` | `satisfaction_label` | `enum_to_enum` (lenient, **int keys**) | Likert code → label. The map is keyed by integers (no cast needed — see below). Lenient so an out-of-range code → `unknown`. |
| `recommend` | `would_recommend` | `cast(int→boolean)` | A true binary needs no lookup — `cast` makes a native bool. |
| `channel` | `channel_group` | `enum_to_enum` (lenient, default `other`) | Open-ended vocabulary; `kiosk` isn't mapped → `other`. |
| `channel` | `channel_strict` | `enum_to_enum` (strict, all mapped) | **Contrast:** the fail-fast alternative for a hard-contract vocabulary. |

### strict vs. lenient — the same column, both ways

Row R4's `channel = kiosk`:
- `channel_group` → `other` (lenient default keeps the import running).
- `channel_strict` → `self_service` (it *is* mapped here, so it succeeds).

If a value were outside a **strict** map, it raises an error:

```python
EnumToEnum({"web": "digital", "phone": "assisted", "kiosk": "self_service"},
           strict=True).transform("mail")
# KeyError: Missing mapping for value: mail
```

Choose **strict** when the code set is guaranteed and an unexpected value must
halt the import; choose **lenient + default** when intake data drifts and you'd
rather flag than fail.

### Integer keys round-trip safely

`satisfaction_label` maps integer codes (`1`–`5`) to **string** labels, and the
map is keyed by integers directly. That works in-memory *and* through
`rules.json` because `EnumToEnum` serializes its mapping as a list of
`{"from", "to"}` entries rather than a JSON object:

```json
"mapping": [{"from": 1, "to": "very_dissatisfied"}, ...]
```

A JSON *object* can only have string keys, so an object form would have turned
`1` into `"1"` on save — and the integer input would then miss every key and
fall through to the default. The entry-list keeps each key in a value position,
so its type is preserved (`1` stays the integer `1`). No `cast(int→text)` is
needed. (Examples 06 and 08 rely on the same property to feed a one-hot integer
index straight into `enum_to_enum`.)

## The rules, serialized

The full rule set for this example, in both formats. `RuleSet.save()` and `load()` (and the CLI's `--rules`) pick the format from the file extension (`.yaml`/`.yml` for YAML, otherwise JSON), and both load identically.

`rules.json`:

```json
[
  {
    "sources": [
      "satisfaction"
    ],
    "target": "satisfaction_label",
    "operations": [
      {
        "operation": "enum_to_enum",
        "mapping": [
          {
            "from": 1,
            "to": "very_dissatisfied"
          },
          {
            "from": 2,
            "to": "dissatisfied"
          },
          {
            "from": 3,
            "to": "neutral"
          },
          {
            "from": 4,
            "to": "satisfied"
          },
          {
            "from": 5,
            "to": "very_satisfied"
          }
        ],
        "strict": false,
        "default": "unknown"
      }
    ],
    "metadata": {
      "rationale": "Likert int -> label, keyed by integers (the serialized form preserves key type, so no cast is needed); lenient with default='unknown' for out-of-range codes."
    }
  },
  {
    "sources": [
      "recommend"
    ],
    "target": "would_recommend",
    "operations": [
      {
        "operation": "cast",
        "source": "integer",
        "target": "boolean"
      }
    ],
    "metadata": {
      "rationale": "0/1 flag -> native boolean via cast; no lookup table required for a true binary."
    }
  },
  {
    "sources": [
      "channel"
    ],
    "target": "channel_group",
    "operations": [
      {
        "operation": "enum_to_enum",
        "mapping": [
          {
            "from": "web",
            "to": "digital"
          },
          {
            "from": "phone",
            "to": "assisted"
          }
        ],
        "strict": false,
        "default": "other"
      }
    ],
    "metadata": {
      "rationale": "Open-ended channel vocabulary: map the known set, coerce the rest to 'other' rather than failing."
    }
  },
  {
    "sources": [
      "channel"
    ],
    "target": "channel_strict",
    "operations": [
      {
        "operation": "enum_to_enum",
        "mapping": [
          {
            "from": "web",
            "to": "digital"
          },
          {
            "from": "phone",
            "to": "assisted"
          },
          {
            "from": "kiosk",
            "to": "self_service"
          }
        ],
        "strict": true
      }
    ],
    "metadata": {
      "rationale": "Contrast to channel_group: strict mapping that raises on any unknown code. Use when the vocabulary is a hard contract and an unexpected value must halt the import."
    }
  }
]
```

`rules.yaml`:

```yaml
- sources: [satisfaction]
  target: satisfaction_label
  operations:
  - operation: enum_to_enum
    mapping:
    - {from: 1, to: very_dissatisfied}
    - {from: 2, to: dissatisfied}
    - {from: 3, to: neutral}
    - {from: 4, to: satisfied}
    - {from: 5, to: very_satisfied}
    strict: false
    default: unknown
  metadata: {rationale: 'Likert int -> label, keyed by integers (the serialized form
      preserves key type, so no cast is needed); lenient with default=''unknown''
      for out-of-range codes.'}

- sources: [recommend]
  target: would_recommend
  operations:
  - {operation: cast, source: integer, target: boolean}
  metadata: {rationale: 0/1 flag -> native boolean via cast; no lookup table required
      for a true binary.}

- sources: [channel]
  target: channel_group
  operations:
  - operation: enum_to_enum
    mapping:
    - {from: web, to: digital}
    - {from: phone, to: assisted}
    strict: false
    default: other
  metadata: {rationale: 'Open-ended channel vocabulary: map the known set, coerce
      the rest to ''other'' rather than failing.'}

- sources: [channel]
  target: channel_strict
  operations:
  - operation: enum_to_enum
    mapping:
    - {from: web, to: digital}
    - {from: phone, to: assisted}
    - {from: kiosk, to: self_service}
    strict: true
  metadata: {rationale: 'Contrast to channel_group: strict mapping that raises on
      any unknown code. Use when the vocabulary is a hard contract and an unexpected
      value must halt the import.'}
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
...,satisfaction_label,would_recommend,channel_group,channel_strict,...
R1,...,very_satisfied,True,digital,digital,...
R4,...,satisfied,False,other,self_service,...
```
