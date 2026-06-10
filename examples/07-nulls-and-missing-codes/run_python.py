"""
Example 07 — run via the Python API and verify against the golden master.

See build_rules.py for the per-rule rationale. The Python `harmonize_file`
output keeps all input columns plus the targets and metadata, which is what
`expected_output.csv` captures.
"""

import sys
from pathlib import Path

from harmonization_framework import RuleSet
from harmonization_framework.harmonize import harmonize_file

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_shared"))
from check_output import assert_matches  # noqa: E402


def main() -> None:
    rules = RuleSet()
    rules.load(str(HERE / "rules.json"), clean=True)

    harmonize_file(
        input_path=str(HERE / "input.csv"),
        output_path=str(HERE / "output.csv"),
        rules=rules,
        dataset_name="messy",
    )

    assert_matches(HERE / "output.csv", HERE / "expected_output.csv")


if __name__ == "__main__":
    main()
