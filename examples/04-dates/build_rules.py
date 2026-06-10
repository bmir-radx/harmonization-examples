"""
Chapter 04 — Dates (rule definitions / SOURCE OF TRUTH).

Normalizing date/time fields to canonical formats with `convert_date`.

The key behaviour to internalize: **convert_date is strict.** A value that does
not match `source_format` raises a ValueError rather than guessing. For dates
this is the right default — a silently mis-parsed date corrupts data quietly,
which is worse than a loud failure. (See the README for a demonstration of the
fail-fast path against bad_input.csv.)

Note: the framework has no fuzzy/multi-format date parser, so each rule pins a
single exact source format. Mixed-format columns must be split or pre-cleaned.

Regenerate rules.json:
    ../../../harmonization-framework/venv/bin/python build_rules.py
"""

from pathlib import Path

from harmonization_framework import HarmonizationRule, RuleSet
from harmonization_framework.primitives import ConvertDate


def build() -> RuleSet:
    rules = RuleSet()

    # --- ordered_at (datetime) -> order_date (date only) --------------------
    # Drop the time-of-day by reformatting to a date-only canonical form.
    rules.add_rule(
        HarmonizationRule(
            sources=["ordered_at"],
            target="order_date",
            transformation=[ConvertDate("%Y-%m-%d %H:%M:%S", "%Y-%m-%d")],
            metadata={
                "rationale": "Reduce a full timestamp to a canonical date-only "
                "field; the time component is not needed downstream."
            },
        )
    )

    # --- ordered_at (datetime) -> order_month (human label) -----------------
    # Same source, a coarser presentation grain ("Jan 2025"). Two rules off one
    # column produce date and month views without re-parsing upstream.
    rules.add_rule(
        HarmonizationRule(
            sources=["ordered_at"],
            target="order_month",
            transformation=[ConvertDate("%Y-%m-%d %H:%M:%S", "%b %Y")],
            metadata={
                "rationale": "Month-grain label for reporting/rollups, derived "
                "from the same timestamp."
            },
        )
    )

    # --- delivered_on (date) -> delivered_us (US display) -------------------
    # A date already in ISO form, reformatted to US MM/DD/YYYY for display.
    rules.add_rule(
        HarmonizationRule(
            sources=["delivered_on"],
            target="delivered_us",
            transformation=[ConvertDate("%Y-%m-%d", "%m/%d/%Y")],
            metadata={
                "rationale": "Reformat ISO date to US display format. Source is "
                "date-only, so the source_format has no time component."
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
