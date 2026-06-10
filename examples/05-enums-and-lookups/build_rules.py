"""
Chapter 05 — Enums & Lookups (rule definitions / SOURCE OF TRUTH).

Mapping coded values to a target vocabulary, with two lessons:

  1. strict=True (fail fast) vs. strict=False + default (coerce + flag): pick
     per field based on whether the code set is guaranteed.
  2. Integer-keyed maps just work: you can key an EnumToEnum by integers and
     map them to string labels. The serialized form is a list of {from, to}
     entries (not a JSON object), so the integer keys keep their type through a
     rules.json round-trip and match integer inputs directly — no Cast-to-text
     dance required. (The same is true of the one-hot reduction in chapters
     06/08, which now feed their integer index straight into EnumToEnum.)

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
    # Likert integer code to a string label. We key the map by integers and map
    # them to string labels directly: the serialized form preserves the integer
    # keys (see lesson 2 above), so the lookup matches the integer CSV value
    # identically in-memory and after a save()/load() round-trip — no cast
    # needed. Lenient with default='unknown' so an out-of-range code doesn't
    # crash a survey import.
    rules.add_rule(
        HarmonizationRule(
            sources=["satisfaction"],
            target="satisfaction_label",
            transformation=[
                EnumToEnum(
                    mapping={
                        1: "very_dissatisfied",
                        2: "dissatisfied",
                        3: "neutral",
                        4: "satisfied",
                        5: "very_satisfied",
                    },
                    default="unknown",
                    strict=False,
                ),
            ],
            metadata={
                "rationale": "Likert int -> label, keyed by integers (the "
                "serialized form preserves key type, so no cast is needed); "
                "lenient with default='unknown' for out-of-range codes."
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
    here = Path(__file__).resolve().parent
    # Save the same rules in both formats. rules.json is the primary artifact;
    # rules.yaml is the equivalent YAML serialization (the framework loads
    # either, picking the format by file extension).
    rules.save(str(here / "rules.json"))
    rules.save(str(here / "rules.yaml"))
    print(f"Wrote {len(rules)} rules to rules.json and rules.yaml")


if __name__ == "__main__":
    main()
