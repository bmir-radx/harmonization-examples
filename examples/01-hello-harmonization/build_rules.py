"""
Example 01 — Hello Harmonization (rule definitions / SOURCE OF TRUTH).

This is the smallest possible end-to-end harmonization. It introduces the two
ideas every later example builds on:

  1. A *rule* maps one or more SOURCE columns to a single TARGET column, by
     running the source value(s) through an ordered list of *primitive
     operations* (the "transformation").
  2. A *RuleSet* is just a collection of rules. You build it in Python, then
     `save()` it to JSON. The CLI and the RPC sidecar consume that JSON, so the
     Python code here is the single source of truth for all three interfaces.

Run this file to (re)generate `rules.json`:

    ../../harmonization-framework/venv/bin/python build_rules.py
"""

from pathlib import Path

from harmonization_framework import HarmonizationRule, RuleSet
from harmonization_framework.primitives import DoNothing, EnumToEnum


def build() -> RuleSet:
    rules = RuleSet()

    # --- Rule 1: pass a column through unchanged, only renaming it. ----------
    # `full_name` is already clean; we just want it to land in a target column
    # called `name`. A rule with a single `DoNothing` operation is the
    # idiomatic way to express "rename / carry across with no transformation".
    # We could give it an empty transformation list, but `DoNothing` documents
    # the intent explicitly and serializes to a visible operation.
    rules.add_rule(
        HarmonizationRule(
            sources=["full_name"],
            target="name",
            transformation=[DoNothing()],
            metadata={
                "rationale": "Source is already clean; carry it across under "
                "the canonical column name with no transformation."
            },
        )
    )

    # --- Rule 2: map short status codes to human-readable labels. ------------
    # The source uses single-letter codes; the target schema wants full words.
    # `EnumToEnum` is a lookup table. We leave `strict=False` (the default) so
    # that an *unexpected* code does not crash the whole run — instead it maps
    # to `default`. Here we choose default="unknown" rather than None so the
    # output is self-explaining: a reader sees that a value fell outside the
    # known set, instead of an empty cell that could mean several things.
    rules.add_rule(
        HarmonizationRule(
            sources=["status_code"],
            target="status",
            transformation=[
                EnumToEnum(
                    mapping={"A": "active", "I": "inactive", "P": "pending"},
                    default="unknown",
                    strict=False,
                )
            ],
            metadata={
                "rationale": "Codes are controlled but data entry is imperfect; "
                "map known codes and surface anything unexpected as 'unknown' "
                "rather than failing the batch or emitting a blank."
            },
        )
    )

    return rules


def main() -> None:
    rules = build()
    out_path = Path(__file__).resolve().parent / "rules.json"
    rules.save(str(out_path))
    print(f"Wrote {len(rules)} rules to {out_path}")


if __name__ == "__main__":
    main()
