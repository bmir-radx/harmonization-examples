"""
Example 04 — Dates — run via the Python API using the YAML rules, and verify the output.

Identical to run_python.py except it loads `rules.yaml` instead of `rules.json`.
The framework picks the format from the file extension, so the YAML rules
produce exactly the same harmonized output — checked here against the same
`expected_output.csv`.
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
    rules.load(str(HERE / "rules.yaml"), clean=True)

    harmonize_file(
        input_path=str(HERE / "input.csv"),
        output_path=str(HERE / "output_yaml.csv"),
        rules=rules,
        dataset_name="events",
    )

    assert_matches(HERE / "output_yaml.csv", HERE / "expected_output.csv")


if __name__ == "__main__":
    main()
