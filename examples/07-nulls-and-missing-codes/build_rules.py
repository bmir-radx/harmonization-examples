"""
Chapter 07 — Nulls & Missing-Value Codes (rule definitions / SOURCE OF TRUTH).

How the framework treats missing data, and how to handle the "fake nulls"
(missing-value codes) that pollute real datasets.

Verified null semantics:
  - A genuine null (None, float('nan'), or pd.NA) PASSES THROUGH most scalar
    primitives unchanged (scale, round, cast, enum_to_enum's input, ...).
  - A blank CSV cell reads as a null and therefore passes through untouched.

The real trap is MISSING-VALUE CODES — `UNK`, `-999`, `N/A` — which are NOT null
to pandas. They are ordinary values that flow through transforms and corrupt
results unless you handle them explicitly. Two patterns:

  A. Categorical code, known vocabulary: map real values AND the missing-value
     code (code -> None) in one enum_to_enum; `default` then only catches truly
     unexpected values. (Demonstrated below for `result`.)
  B. Numeric code (e.g. -999): use the `missing_code` primitive, which maps each
     declared code to a real null and passes every other value through
     unchanged — the identity-preserving null map enum_to_enum can't express.
     Each code carries a label ("not_measured"); the engine reports every nulled
     cell, with its label and row, to the replay log. (Demonstrated below for
     `reading_lb`.)

Primitives: enum_to_enum (categorical codes), missing_code (numeric codes),
scale (null pass-through).

Regenerate rules.json:
    ../../../harmonization-framework/venv/bin/python build_rules.py
"""

from pathlib import Path

from harmonization_framework import HarmonizationRule, RuleSet
from harmonization_framework.primitives import EnumToEnum, MissingCode, Scale


def build() -> RuleSet:
    rules = RuleSet()

    # --- result -> result_clean (PATTERN A: missing-value code -> null) -----
    # Known categorical vocabulary {pos, neg} plus the missing-value code UNK.
    # We map all three: pos/neg to canonical labels, and UNK -> None (a real
    # null). Because every legitimate value is mapped, `default` only fires for
    # genuinely unexpected codes — here default="unexpected" so a surprise is
    # visible rather than silently nulled. This is the safe way to null a
    # missing-value code without clobbering real data.
    rules.add_rule(
        HarmonizationRule(
            sources=["result"],
            target="result_clean",
            transformation=[
                EnumToEnum(
                    mapping={"pos": "positive", "neg": "negative", "UNK": None},
                    default="unexpected",
                    strict=False,
                )
            ],
            metadata={
                "rationale": "Missing-value code 'UNK' -> null by mapping it "
                "explicitly alongside the real vocabulary; default flags only "
                "truly unexpected codes. (No null_if primitive exists.)"
            },
        )
    )

    # --- score -> score_x10 (genuine null PASS-THROUGH) ---------------------
    # `score` has genuine blank cells (rows N2, N4) which read as null.
    # `scale` passes a null straight through: the output stays blank. No special
    # handling needed for real nulls — only for code values.
    rules.add_rule(
        HarmonizationRule(
            sources=["score"],
            target="score_x10",
            transformation=[Scale(10)],
            metadata={
                "rationale": "A genuine null passes through `scale` unchanged; "
                "a blank input cell yields a blank output cell."
            },
        )
    )

    # --- reading_lb -> reading_kg (numeric code handled with missing_code) ---
    # reading_lb uses -999 as a 'missing' code (row N3). -999 is NOT null to
    # pandas, so a bare Scale would multiply it and the code would survive,
    # CORRUPTED, into the output (-999 * 0.453592 ~= -453.14). enum_to_enum can't
    # null just -999 (its default would null every reading), so we use
    # missing_code: it maps each declared code to a real null and passes every
    # other value through unchanged. missing_code runs FIRST (on the raw source),
    # turning -999 into None; `scale` then passes the null through, so
    # reading_kg is blank for N3 instead of corrupted. The code's
    # label ("not_measured") is reported per-row to the replay log.
    rules.add_rule(
        HarmonizationRule(
            sources=["reading_lb"],
            target="reading_kg",
            transformation=[
                MissingCode(codes={-999: "not_measured"}),
                Scale(0.45359237),
            ],
            metadata={
                "rationale": "Numeric missing-value code -999 -> null via "
                "missing_code (identity-preserving: other readings pass through), "
                "then Scale passes the null through. The label is reported to the "
                "replay log."
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
