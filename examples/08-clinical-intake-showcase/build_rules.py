"""
Example 08 — Clinical Intake Showcase (rule definitions / SOURCE OF TRUTH).

A deliberately realistic intake CSV with the messes you actually hit:
  - names stored as "Last, First" with inconsistent whitespace and casing,
  - site-specific visit codes (including one outside the controlled set),
  - dates in a non-target format,
  - height in inches,
  - consent captured as THREE separate one-hot flag columns.

This example blends primitives from the tutorials and, more importantly,
demonstrates the *harmonization decisions* that matter in practice: when to
fail vs. coerce vs. default, how to resolve many-columns-to-one-column, and
how to keep those decisions auditable via rule metadata.

Primitives: substitute, normalize_text, convert_date, convert_units, round,
reduce (one-hot), enum_to_enum.

Regenerate rules.json:
    ../../../harmonization-framework/venv/bin/python build_rules.py
"""

from pathlib import Path

from harmonization_framework import HarmonizationRule, RuleSet
from harmonization_framework.primitives import (
    ConvertDate,
    ConvertUnits,
    EnumToEnum,
    NormalizeText,
    Reduce,
    Round,
    Substitute,
    Unit,
)
from harmonization_framework.primitives.normalize import Normalization
from harmonization_framework.primitives.reduce import Reduction


def build() -> RuleSet:
    rules = RuleSet()

    # --- patient_name "Last, First" -> family_name -------------------------
    # Pipeline: extract the part before the comma, strip whitespace, then
    # collapse to title-ish form by lowercasing (row 1002 arrives as
    # "  turing,  alan "). We DON'T title-case here (the framework has no
    # title primitive); we normalise to lower so downstream matching is
    # case-stable. Substitute first because it defines the field; normalise
    # second to clean whatever it extracted.
    rules.add_rule(
        HarmonizationRule(
            sources=["patient_name"],
            target="family_name",
            transformation=[
                Substitute(r"^\s*([^,]+?)\s*,.*$", r"\1"),
                NormalizeText(Normalization.LOWER),
            ],
            metadata={
                "rationale": "Extract surname (before comma), then lowercase to "
                "absorb inconsistent casing/whitespace across sites."
            },
        )
    )

    # --- patient_name "Last, First" -> given_name --------------------------
    # Same source, different target: pull the part AFTER the comma. Two rules
    # reading one column is the idiomatic way to split a field.
    rules.add_rule(
        HarmonizationRule(
            sources=["patient_name"],
            target="given_name",
            transformation=[
                Substitute(r"^[^,]*,\s*(.+?)\s*$", r"\1"),
                NormalizeText(Normalization.LOWER),
            ],
            metadata={
                "rationale": "Extract given name (after comma), then lowercase; "
                "mirrors the family_name rule on the same source column."
            },
        )
    )

    # --- visit_code -> visit_type ------------------------------------------
    # Controlled vocabulary, but site 1004 sent "XX" (outside the set). We use
    # strict=False with an explicit default so the unknown code is surfaced as
    # "unmapped" instead of crashing the whole intake batch. This is the core
    # fail-vs-coerce decision: for a non-critical label we coerce + flag.
    rules.add_rule(
        HarmonizationRule(
            sources=["visit_code"],
            target="visit_type",
            transformation=[
                EnumToEnum(
                    mapping={
                        "BL": "baseline",
                        "FU": "follow_up",
                        "SC": "screening",
                    },
                    default="unmapped",
                    strict=False,
                )
            ],
            metadata={
                "rationale": "Site codes drift; map the known set and surface "
                "anything else as 'unmapped' rather than failing the batch."
            },
        )
    )

    # --- visit_date YYYY-MM-DD -> visit_date_us MM/DD/YYYY -----------------
    # ConvertDate is strict by design: a value that doesn't match the source
    # format RAISES. That's the right call for dates — a silently mis-parsed
    # date is worse than a loud failure — so here we accept fail-fast semantics
    # for the date field even though we coerced the visit code above.
    rules.add_rule(
        HarmonizationRule(
            sources=["visit_date"],
            target="visit_date_us",
            transformation=[ConvertDate("%Y-%m-%d", "%m/%d/%Y")],
            metadata={
                "rationale": "Reformat to US display format. ConvertDate fails "
                "fast on malformed dates by design — preferable to a silent "
                "misparse for a clinically meaningful field."
            },
        )
    )

    # --- height_in -> height_cm --------------------------------------------
    rules.add_rule(
        HarmonizationRule(
            sources=["height_in"],
            target="height_cm",
            transformation=[ConvertUnits(Unit.INCH, Unit.CENTIMETER), Round(1)],
            metadata={"rationale": "Convert at full precision, then round to 1 dp."},
        )
    )

    # --- (consent_research, consent_biobank, consent_none) -> consent_type --
    # MANY-TO-ONE: three mutually exclusive one-hot flag columns collapse to a
    # single categorical. Reduce(ONE-HOT) returns the index of the single set
    # bit (0/1/2), then EnumToEnum names it. If a row had zero or multiple
    # flags set, one-hot returns None and EnumToEnum maps None -> default
    # ("ambiguous"), turning a data-quality problem into a visible value rather
    # than a wrong one. The source ORDER defines the index mapping, so the
    # sources list and the EnumToEnum keys must stay aligned.
    #
    # The integer index feeds EnumToEnum directly, keyed by ints 0/1/2. No
    # cast-to-text is needed: EnumToEnum serializes its mapping as a list of
    # {from, to} entries, so the integer keys keep their type through a
    # save()/load() round-trip and match the integer index identically in-memory
    # and from rules.json.
    rules.add_rule(
        HarmonizationRule(
            sources=["consent_research", "consent_biobank", "consent_none"],
            target="consent_type",
            transformation=[
                Reduce(Reduction.ONEHOT),
                EnumToEnum(
                    mapping={0: "research", 1: "biobank", 2: "declined"},
                    default="ambiguous",
                    strict=False,
                ),
            ],
            metadata={
                "rationale": "Collapse 3 mutually-exclusive one-hot consent "
                "flags into one categorical; rows with zero/multiple flags "
                "become 'ambiguous' (one-hot -> None -> default) instead of a "
                "silently wrong label. Integer index keys EnumToEnum directly "
                "(serialized form preserves key type). Source order = index."
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
