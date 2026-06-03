# 05 — Enums & Lookups

Mapping coded values to a target vocabulary, and the strict-vs-lenient decision
in depth.

## What it teaches

- `enum_to_enum` — the lookup-table primitive.
- `cast` — type coercion (int → text, int → boolean).
- **`strict=True` vs. `strict=False` + `default`**, side by side on one column.
- The **integer-key serialization gotcha** and its fix.

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
| `satisfaction` | `satisfaction_label` | `cast(int→text)` → `enum_to_enum` (lenient) | Likert code → label. **Cast to text** so string keys survive JSON round-trip (see below). Lenient so an out-of-range code → `unknown`. |
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

### The integer-key serialization gotcha

`EnumToEnum.from_serialization` only restores **integer** keys from JSON when
*both* keys and values are int-like. `satisfaction_label` maps integer codes to
**string** labels, so after `save()`/`load()` the keys come back as strings
(`"1"`, …). An integer input would then miss every key and fall to the default.

**Fix:** `cast(int→text)` first, and key the map by `"1".."5"`. The lookup then
behaves identically in-memory and through `rules.json`. (Example 08 applies the
same fix to a one-hot reduction index.)

## Running it

```bash
../../../harmonization-framework/venv/bin/python build_rules.py
../../../harmonization-framework/venv/bin/python run_python.py
bash run_cli.sh
node client.ts   # start the sidecar first
```

## Expected output

```
...,satisfaction_label,would_recommend,channel_group,channel_strict,...
R1,...,very_satisfied,True,digital,digital,...
R4,...,satisfied,False,other,self_service,...
```
