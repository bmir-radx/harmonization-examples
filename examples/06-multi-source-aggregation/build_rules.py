"""
Example 06 — Multi-source Aggregation (rule definitions / SOURCE OF TRUTH).

Rules whose `sources` list has MORE THAN ONE column, collapsing several inputs
into one target. Plus the single-column variant: a packed-array cell parsed and
reduced.

How a multi-source rule feeds the pipeline (verified behaviour):
  - The framework passes a LIST (one element per source, in `sources` order)
    into the transformation. List-consuming primitives (Reduce, MapEach) take
    that list directly.
  - Reduce and MapEach REJECT nulls (a null element raises) — a missing source
    is a data-quality signal, not silently dropped. Use the CLI --on-missing
    policy for whole-column absence.
  - Reduce(ONE-HOT) returns the index of the single set bit, or None if the
    inputs don't sum to exactly 1. Source ORDER defines the index.

Primitives: reduce (sum / one-hot), parse_array, enum_to_enum.

Regenerate rules.json:
    ../../../harmonization-framework/venv/bin/python build_rules.py
"""

from pathlib import Path

from harmonization_framework import HarmonizationRule, RuleSet
from harmonization_framework.primitives import EnumToEnum, ParseArray, Reduce
from harmonization_framework.primitives.reduce import Reduction


def build() -> RuleSet:
    rules = RuleSet()

    # --- (sym_fever, sym_cough, sym_fatigue) -> symptom_count ---------------
    # Three independent binary flags SUMMED into a count. Unlike one-hot, these
    # are not mutually exclusive, so SUM (not ONE-HOT) is the right reduction.
    rules.add_rule(
        HarmonizationRule(
            sources=["sym_fever", "sym_cough", "sym_fatigue"],
            target="symptom_count",
            transformation=[Reduce(Reduction.SUM)],
            metadata={
                "rationale": "Independent (non-exclusive) symptom flags -> a "
                "count via SUM. ONE-HOT would be wrong: more than one can be set."
            },
        )
    )

    # --- (stat_new, stat_active, stat_closed) -> triage_status --------------
    # Mutually exclusive status flags -> one categorical. ONE-HOT yields the
    # index of the set bit (0/1/2); EnumToEnum names it. The map is keyed by the
    # integer index directly — the serialized form preserves integer keys, so no
    # cast-to-text is needed. Source order defines the index, so it must match
    # the mapping keys.
    rules.add_rule(
        HarmonizationRule(
            sources=["stat_new", "stat_active", "stat_closed"],
            target="triage_status",
            transformation=[
                Reduce(Reduction.ONEHOT),
                EnumToEnum(
                    mapping={0: "new", 1: "active", 2: "closed"},
                    default="ambiguous",
                    strict=False,
                ),
            ],
            metadata={
                "rationale": "Mutually-exclusive status flags -> one label via "
                "ONE-HOT. Source order = index order. Zero/multiple set bits "
                "give None -> 'ambiguous'. The integer index feeds EnumToEnum "
                "directly — keys are kept as ints through serialization."
            },
        )
    )

    # --- daily_scores (packed "a|b|c") -> score_total -----------------------
    # A SINGLE column holding many values. This is a single-source rule, so the
    # transformation receives the scalar string; parse_array turns it into a
    # list of ints, then Reduce(SUM) collapses it. parse_array is strict by
    # default, so a malformed cell raises rather than silently yielding garbage.
    rules.add_rule(
        HarmonizationRule(
            sources=["daily_scores"],
            target="score_total",
            transformation=[
                ParseArray(format="delimiter", delimiter="|", item_type="integer"),
                Reduce(Reduction.SUM),
            ],
            metadata={
                "rationale": "Packed multi-value cell: parse_array -> list of "
                "ints, then SUM. Demonstrates aggregation within one column."
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
