"""
Example 05 — Enums & Lookups (rule definitions / SOURCE OF TRUTH).

Mapping coded values to a target vocabulary, with two lessons:

  1. strict=True (fail fast) vs. strict=False + default (coerce + flag): pick
     per field based on whether the code set is guaranteed.
  2. The integer-key serialization gotcha: EnumToEnum only restores INTEGER
     keys from JSON when BOTH keys and values are int-like. If you map integer
     codes to STRING labels, the keys round-trip as strings — so an integer
     input misses every key. Fix: Cast the input to text and key the map by
     strings. (Same fix used for the one-hot reduction in example 08.)

Primitives: cast, enum_to_enum.

Regenerate rules.json:
    ../../../harmonization-framework/venv/bin/python build_rules.py
"""

from pathlib import Path

from harmonization_framework import HarmonizationRule, RuleSet
from harmonization_framework.primitives import Cast, EnumToEnum


def build() -> RuleSet:
    rules = RuleSet()

    # --- satisfaction (int 1..5) -> satisfaction_label ----------------------
    # Likert code to a string label. The CSV value is an integer, but our map
    # values are strings, so (per the gotcha above) the JSON keys would come
    # back as strings. We Cast("integer","text") first and key the map by
    # "1".."5" so the lookup matches identically in-memory and after a
    # save()/load() round-trip through rules.json.
    rules.add_rule(
        HarmonizationRule(
            sources=["satisfaction"],
            target="satisfaction_label",
            transformation=[
                Cast("integer", "text"),
                EnumToEnum(
                    mapping={
                        "1": "very_dissatisfied",
                        "2": "dissatisfied",
                        "3": "neutral",
                        "4": "satisfied",
                        "5": "very_satisfied",
                    },
                    default="unknown",
                    strict=False,
                ),
            ],
            metadata={
                "rationale": "Likert int -> label. Cast to text so the string "
                "keys survive JSON round-trip; lenient with default='unknown' "
                "since out-of-range codes shouldn't crash a survey import."
            },
        )
    )

    # --- recommend (0/1) -> would_recommend (boolean) -----------------------
    # cast does the work directly: integer 0/1 -> Python bool. No mapping
    # needed. Shows cast as a standalone coercion, distinct from enum_to_enum.
    rules.add_rule(
        HarmonizationRule(
            sources=["recommend"],
            target="would_recommend",
            transformation=[Cast("integer", "boolean")],
            metadata={
                "rationale": "0/1 flag -> native boolean via cast; no lookup "
                "table required for a true binary."
            },
        )
    )

    # --- channel -> channel_group (LENIENT) ---------------------------------
    # "kiosk" is intentionally NOT in the map to exercise the default path:
    # unknown channels coerce to "other" and stay visible. Use this when the
    # source vocabulary is open-ended / drifts.
    rules.add_rule(
        HarmonizationRule(
            sources=["channel"],
            target="channel_group",
            transformation=[
                EnumToEnum(
                    mapping={"web": "digital", "phone": "assisted"},
                    default="other",
                    strict=False,
                )
            ],
            metadata={
                "rationale": "Open-ended channel vocabulary: map the known set, "
                "coerce the rest to 'other' rather than failing."
            },
        )
    )

    # --- channel -> channel_strict (STRICT, contrast) -----------------------
    # SAME source, but strict=True with every value mapped. This documents the
    # fail-fast alternative: if "kiosk" were absent here it would raise. We map
    # all three so the happy path succeeds; the README explains how to see it
    # fail. Choose strict when the code set is a hard contract.
    rules.add_rule(
        HarmonizationRule(
            sources=["channel"],
            target="channel_strict",
            transformation=[
                EnumToEnum(
                    mapping={"web": "digital", "phone": "assisted", "kiosk": "self_service"},
                    strict=True,
                )
            ],
            metadata={
                "rationale": "Contrast to channel_group: strict mapping that "
                "raises on any unknown code. Use when the vocabulary is a hard "
                "contract and an unexpected value must halt the import."
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
