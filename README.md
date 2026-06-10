# Harmonization Examples

A layered, self-checking set of examples for the harmonization framework — a
tool for mapping varied source data onto a single, canonical schema with
consistent column names and consistent values.

- **Guide / docs site:** https://bmir-radx.github.io/harmonization-examples/
- **Examples:** [`examples/`](examples/)

Each example maps a small, purpose-built input onto a canonical schema and
verifies its output against a committed **golden master**, so the code you read
is code that is known to work. The examples are layered: start with
[`01-hello-harmonization`](examples/01-hello-harmonization/), which introduces
the rule model, and work upward.

## The rule model

A **RuleSet** is an ordered list of **rules**. Each rule maps one or more
**source** columns to a single **target** column by running the value through a
**transformation** — an ordered list of primitive **operations**.

![Anatomy of a RuleSet](docs/assets/rule-model.svg)

## Running an example

The examples run against the framework installed in the sibling repo's
virtualenv. From the `examples/` directory:

```bash
# Python interface (also runs the golden-master assertion):
../../harmonization-framework/venv/bin/python 01-hello-harmonization/run_python.py

# CLI interface:
bash 01-hello-harmonization/run_cli.sh
```

See [`examples/README.md`](examples/README.md) for the full catalog and how the
examples are structured.

## Building the docs locally

```bash
pip install -r requirements-docs.txt
mkdocs serve
```

The site is also built and published to GitHub Pages on every push to `main`
(see [`.github/workflows/docs.yml`](.github/workflows/docs.yml)).
