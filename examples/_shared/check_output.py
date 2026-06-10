"""
Shared golden-output verification helper for the harmonization examples.

Every built example ships a known-good `expected_output.csv`. After an example
runs, it calls `assert_matches(...)` to confirm the freshly produced CSV still
equals the golden master. This turns each example into a self-checking regression
test: if a future change to the framework alters behaviour, the example fails
loudly instead of silently drifting.

Why compare as strings rather than as floats?
    The harmonized CSVs are the *contract* the examples teach. We compare the
    rendered CSV cells exactly (after normalising blank/NA spelling) so the
    documented `expected_output.csv` is literally what the tool emits. Numeric
    rounding/formatting is therefore part of what each example demonstrates and
    is pinned by the golden master.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


def _normalise(df: pd.DataFrame) -> pd.DataFrame:
    # Read everything back as strings and unify the many spellings of "missing"
    # (empty cell, NaN, <NA>) into a single empty token so cosmetic differences
    # in how pandas renders nulls never cause a spurious mismatch.
    out = df.astype("string")
    out = out.where(~out.isna(), "")
    out = out.replace({"<NA>": "", "nan": "", "NaN": ""})
    return out


def assert_matches(actual_path: str | Path, expected_path: str | Path) -> None:
    """
    Assert that the CSV at `actual_path` matches the golden CSV at
    `expected_path`, raising AssertionError with a readable diff on mismatch.
    """
    actual_path = Path(actual_path)
    expected_path = Path(expected_path)

    actual = _normalise(pd.read_csv(actual_path, dtype=str, keep_default_na=True))
    expected = _normalise(pd.read_csv(expected_path, dtype=str, keep_default_na=True))

    if list(actual.columns) != list(expected.columns):
        raise AssertionError(
            "Column mismatch:\n"
            f"  expected: {list(expected.columns)}\n"
            f"  actual:   {list(actual.columns)}"
        )

    if actual.shape != expected.shape:
        raise AssertionError(
            f"Shape mismatch: expected {expected.shape}, got {actual.shape}"
        )

    if not actual.equals(expected):
        # Surface the first few differing cells to make failures debuggable.
        diffs = []
        for col in expected.columns:
            mism = actual[col] != expected[col]
            for idx in actual.index[mism][:5]:
                diffs.append(
                    f"  row {idx}, col {col!r}: "
                    f"expected {expected.at[idx, col]!r}, got {actual.at[idx, col]!r}"
                )
        raise AssertionError("Cell mismatches:\n" + "\n".join(diffs[:20]))

    print(f"OK: {actual_path.name} matches {expected_path.name}")


if __name__ == "__main__":
    # Usage: python check_output.py <actual.csv> <expected.csv>
    assert_matches(sys.argv[1], sys.argv[2])
