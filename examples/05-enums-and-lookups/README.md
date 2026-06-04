# 05 — Enums & Lookups

Mapping coded values to a target vocabulary, and the strict-vs-lenient decision
in depth.

## What it teaches

- `enum_to_enum` — the lookup-table primitive.
- `cast` — type coercion (int → boolean).
- **`strict=True` vs. `strict=False` + `default`**, side by side on one column.
- That **integer-keyed maps round-trip safely** — you can key a map by integers
  and map them to string labels with no special handling.

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

If a value were outside a **strict** map, it raises:

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

## Running it

```bash
../../../harmonization-framework/venv/bin/python build_rules.py
../../../harmonization-framework/venv/bin/python run_python.py
bash run_cli.sh
```

## Expected output

```
...,satisfaction_label,would_recommend,channel_group,channel_strict,...
R1,...,very_satisfied,True,digital,digital,...
R4,...,satisfied,False,other,self_service,...
```
