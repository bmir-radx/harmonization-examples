"""
Chapter 03 — Text & Names (rule definitions / SOURCE OF TRUTH).

Cleaning free-text fields is the most error-prone part of most harmonizations.
The recurring lesson here: **extract/clean structure with `substitute` FIRST,
then `normalize_text` the result** — normalizing the whole field up front can
destroy the anchors your regex relies on.

Primitives: substitute, normalize_text (strip/upper/remove_accents), truncate.

Regenerate rules.json:
    ../../../harmonization-framework/venv/bin/python build_rules.py
"""

from pathlib import Path

from harmonization_framework import HarmonizationRule, RuleSet
from harmonization_framework.primitives import NormalizeText, Substitute, Truncate
from harmonization_framework.primitives.normalize import Normalization


def build() -> RuleSet:
    rules = RuleSet()

    # --- raw_name -> display_name -------------------------------------------
    # Three ordered substitutions then a strip:
    #   1. drop a leading honorific (Dr./Mr./Mrs./Ms./Prof.), case-insensitive,
    #   2. collapse runs of whitespace to a single space,
    #   3. NormalizeText(STRIP) trims the ends.
    # Order matters: we strip the honorific while it still sits at the start of
    # the string; collapsing whitespace first would still work, but stripping
    # ends FIRST and then matching `^\s*` would be redundant. Keeping the
    # whitespace-collapse before the final strip yields a single clean line.
    rules.add_rule(
        HarmonizationRule(
            sources=["raw_name"],
            target="display_name",
            transformation=[
                Substitute(r"(?i)^\s*(dr|mr|mrs|ms|prof)\.?\s+", ""),
                Substitute(r"\s+", " "),
                NormalizeText(Normalization.STRIP),
            ],
            metadata={
                "rationale": "Strip honorific prefix, collapse internal "
                "whitespace, trim ends. Substitutions run before the strip so "
                "the regex anchors (^) still see the original leading text."
            },
        )
    )

    # --- raw_name -> name_ascii ---------------------------------------------
    # Same cleaning, plus remove_accents for an ASCII-folded variant useful for
    # case-insensitive matching/joining (José -> Jose, ÅSA -> ASA, Síle -> Sile).
    # remove_accents uses NFKD, which also folds ligatures/superscripts; that's
    # desirable here. Accent-folding LAST so it operates on already-clean text.
    rules.add_rule(
        HarmonizationRule(
            sources=["raw_name"],
            target="name_ascii",
            transformation=[
                Substitute(r"(?i)^\s*(dr|mr|mrs|ms|prof)\.?\s+", ""),
                Substitute(r"\s+", " "),
                NormalizeText(Normalization.STRIP),
                NormalizeText(Normalization.ACCENT),
            ],
            metadata={
                "rationale": "ASCII-folded variant for matching/joining. "
                "Accent removal (NFKD) runs last, on already-cleaned text."
            },
        )
    )

    # --- country -> country_code --------------------------------------------
    # A deliberately crude 2-letter code: truncate to 2 chars, uppercase. This
    # is NOT ISO-3166 (Spain -> "SP", not "ES"); it's here to show `truncate`
    # composing with normalization. Real code mapping belongs in an
    # enum_to_enum lookup (see chapter 05) — truncation is the wrong tool for
    # authoritative codes, and saying so is part of the lesson.
    rules.add_rule(
        HarmonizationRule(
            sources=["country"],
            target="country_code",
            transformation=[
                Truncate(2),
                NormalizeText(Normalization.UPPER),
            ],
            metadata={
                "rationale": "Crude 2-letter code via truncate+upper to "
                "demonstrate truncate. For authoritative codes use an "
                "enum_to_enum lookup instead (see chapter 05)."
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
