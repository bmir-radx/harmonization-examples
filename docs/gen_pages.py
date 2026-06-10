"""
Generate the documentation site from the committed example files.

Run automatically by the mkdocs-gen-files plugin at build time (see mkdocs.yml).
For each example directory `examples/NN-name/` it emits a chapter page from that
example's README.md *verbatim* (so the hand-written prose and embedded rule sets
are preserved), then appends a "Data files" section rendering the example's
input.csv and expected_output.csv as Markdown tables read straight from the
committed CSVs — so what the book shows always matches the real files.

The landing page is the top-level examples README (its catalog links are
rewritten to point at the generated chapter pages), and the navigation is
produced as a literate-nav SUMMARY.md.

Nothing here imports the framework or runs an example; it only reads files.
"""

import csv
import re
from pathlib import Path

import mkdocs_gen_files

EXAMPLES = Path("examples")


def csv_to_markdown_table(csv_path: Path, max_rows: int = 50) -> str:
    """Render a CSV file as a GitHub-flavoured Markdown table."""
    with csv_path.open(newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        return "_(empty file)_"
    header, *body = rows
    body = body[:max_rows]

    def cell(value: str) -> str:
        # Escape pipes and show blanks visibly so empty cells aren't ambiguous.
        text = value.replace("|", "\\|")
        return text if text != "" else "&nbsp;"

    lines = [
        "| " + " | ".join(cell(c) for c in header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in body:
        lines.append("| " + " | ".join(cell(c) for c in row) + " |")
    return "\n".join(lines)


def data_files_section(example_dir: Path) -> str:
    """Build a generated 'Data files' section for one example."""
    parts = ["\n\n## Data files\n",
             "_Rendered from the committed CSV files in this example._\n"]
    inp = example_dir / "input.csv"
    exp = example_dir / "expected_output.csv"
    if inp.exists():
        parts.append("\n### `input.csv`\n")
        parts.append(csv_to_markdown_table(inp))
    if exp.exists():
        parts.append("\n\n### `expected_output.csv`\n")
        parts.append(csv_to_markdown_table(exp))
    return "\n".join(parts) + "\n"


def example_dirs():
    return sorted(d for d in EXAMPLES.iterdir()
                  if d.is_dir() and re.match(r"\d\d-", d.name))


nav = mkdocs_gen_files.Nav()

# --- landing page from the top-level examples README -------------------------
# --- landing page: the hand-written tutorial introduction -------------------
intro_md = Path("docs_src/intro.md").read_text()
with mkdocs_gen_files.open("index.md", "w") as f:
    f.write(intro_md)
nav["Introduction"] = "index.md"

# --- one chapter page per example -------------------------------------------
for d in example_dirs():
    readme = d / "README.md"
    if not readme.exists():
        continue
    page = f"{d.name}.md"
    content = readme.read_text().rstrip("\n") + data_files_section(d)
    with mkdocs_gen_files.open(page, "w") as f:
        f.write(content)
    # Nav title: the first H1 of the README, falling back to the dir name.
    m = re.search(r"^#\s+(.*)$", readme.read_text(), re.M)
    title = m.group(1).strip() if m else d.name
    nav[title] = page

# --- reference page: the catalog / structure from the examples README -------
about_md = (EXAMPLES / "README.md").read_text()
# Rewrite catalog links (`NN-name/`) to the generated chapter pages.
about_md = re.sub(r"\]\((\d\d-[a-z0-9-]+)/\)", r"](\1.md)", about_md)
# The README uses GitHub-relative asset paths (`../docs/assets/...`); in the
# built site the page lives at the root and assets are served from `assets/`.
about_md = about_md.replace("../docs/assets/", "assets/")
with mkdocs_gen_files.open("about.md", "w") as f:
    f.write(about_md)
nav["About these examples"] = "about.md"

with mkdocs_gen_files.open("SUMMARY.md", "w") as f:
    f.writelines(nav.build_literate_nav())
