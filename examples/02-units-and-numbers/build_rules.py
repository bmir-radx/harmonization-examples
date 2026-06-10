"""
Chapter 02 — Units & Numbers (rule definitions / SOURCE OF TRUTH).

This example is about NUMERIC harmonization, and its real lesson is that
**operation order matters**. Each rule below is an ordered pipeline; the same
primitives in a different order would give different (often wrong) results. The
comments call out why each order was chosen.

Primitives used: convert_units, scale, round, threshold, bin, format_number.

Regenerate rules.json:
    ../../../harmonization-framework/venv/bin/python build_rules.py
"""

from pathlib import Path

from harmonization_framework import HarmonizationRule, RuleSet
from harmonization_framework.primitives import (
    Bin,
    ConvertUnits,
    FormatNumber,
    Round,
    Scale,
    Threshold,
    Unit,
)


def build() -> RuleSet:
    rules = RuleSet()

    # --- height_in (inches) -> height_cm, rounded to 1 dp. ------------------
    # Order: convert FIRST, round SECOND. Rounding inches to 1 dp and *then*
    # converting would bake in rounding error before the unit scale-up
    # multiplies it. Convert in full precision, then round for presentation.
    rules.add_rule(
        HarmonizationRule(
            sources=["height_in"],
            target="height_cm",
            transformation=[
                ConvertUnits(Unit.INCH, Unit.CENTIMETER),
                Round(1),
            ],
            metadata={
                "rationale": "Convert at full precision, then round. Rounding "
                "before the conversion would amplify rounding error."
            },
        )
    )

    # --- weight_lb -> weight_kg, formatted to 2 dp as a string. -------------
    # `Scale(0.45359237)` is the lb->kg factor. We finish with FormatNumber
    # (not Round) because the target is a *display* field that must always show
    # two decimals (e.g. "52.00", not "52.0"). FormatNumber returns a string;
    # that's deliberate and is the documented way to pin presentation.
    rules.add_rule(
        HarmonizationRule(
            sources=["weight_lb"],
            target="weight_kg",
            transformation=[
                Scale(0.45359237),
                FormatNumber(2),
            ],
            metadata={
                "rationale": "Scale to kg, then FormatNumber(2) to pin a "
                "stable 2-decimal string for display/export."
            },
        )
    )

    # --- oxygen_saturation -> spo2_clamped, a physiologically valid percent. -
    # SpO2 is a percentage and cannot exceed 100; values like 101 are sensor
    # artifacts. Threshold clamps into [0, 100]. We clamp rather than drop so
    # the row is retained and the clamping is a deterministic, auditable choice.
    rules.add_rule(
        HarmonizationRule(
            sources=["oxygen_saturation"],
            target="spo2_clamped",
            transformation=[
                Threshold(lower=0.0, upper=100.0),
            ],
            metadata={
                "rationale": "SpO2 > 100% is physically impossible (sensor "
                "artifact); clamp to [0,100] deterministically instead of "
                "dropping the row."
            },
        )
    )

    # --- age (years) -> age_band, a coarse life-stage label. ----------------
    # Bin requires INTEGER bounds, which suits whole-year ages. Bins must not
    # overlap; the framework validates that. We choose inclusive integer ranges
    # that tile 0..120 with no gaps so every plausible age lands somewhere.
    rules.add_rule(
        HarmonizationRule(
            sources=["age"],
            target="age_band",
            transformation=[
                Bin(
                    [
                        ("child", (0, 12)),
                        ("adolescent", (13, 17)),
                        ("adult", (18, 64)),
                        ("older_adult", (65, 120)),
                    ]
                ),
            ],
            metadata={
                "rationale": "Coarse life-stage bands with inclusive, "
                "non-overlapping integer ranges covering 0..120."
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
