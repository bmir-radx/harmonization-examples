# A Guide to the Harmonization Framework

This is a worked guide to the **harmonization framework** — a tool for
mapping varied source data onto a single, canonical schema with consistent
column names and consistent values. If you have CSV files that *almost* agree —
one calls a field `full_name` and another `patient`, one records status as `A`
and another as `active` — harmonization is the work of bringing them into line,
and this guide teaches the framework by example.

## What you'll learn

By the end you'll be able to read and write harmonization **rules**, choose the
right **primitive operations** for a given cleanup, and reason about the
decisions that matter — when to fail on bad input versus quietly fix it, how to
keep types stable across a save/load, and how to collapse several columns into
one. You don't need prior experience with the framework; you only need to be
comfortable reading a little Python and CSV.

## How to read this guide

The chapters are meant to be read **in order**, starting with chapter 01. Each
one is a small, self-contained example built around a single idea, and later
chapters assume the ideas introduced earlier:

- **01–04** build the foundations: the rule model, then numbers, text, and
  dates.
- **05–07** add the patterns you reach for constantly: lookups, aggregating
  several columns into one, and handling missing data.
- **08** is a realistic showcase that combines everything on one messy intake
  file.

If you're returning to look something up, the chapter list in the sidebar
doubles as a reference — each chapter is named for the primitives it covers.

## What a chapter looks like

Every chapter follows the same shape, so you always know where to look:

- **An introduction** to the problem the chapter addresses.
- **What it teaches** — the primitives and ideas in play.
- **The data** — a small, purpose-built input table.
- **The harmonization choices (and why)** — each rule, with the reasoning behind
  it, not just the mechanics.
- **The rules, serialized** — the complete rule set in both JSON and YAML.
- **Running it** — the commands to reproduce the result yourself.
- **Expected output** and a **Data files** view of the input and the golden
  master.

Every example is also a **self-checking test**: its output is pinned to a
committed **golden master** — an approved reference output the run is checked
against — so the code you read here is code that is known to work. (The term
comes from the "gold master" of audio and film production: the single approved
copy everything else is measured against.)

## The core idea, in brief

You describe a mapping as a set of **rules**. Each rule takes one or more
**source** columns and produces a single **target** column by running the value
through an ordered list of **primitive operations**. A collection of rules is a
**RuleSet**, saved to a `rules.json` (or `rules.yaml`) file. You define the
rules once; the Python API and the command-line tool both read that same file
and produce the same result.

![Anatomy of a RuleSet: a RuleSet is an ordered list of rules; each rule maps source columns through a transformation of operations to a single target column.](assets/rule-model.svg)

That's the whole model. Chapter 01 puts it to work on the smallest possible
example — turn the page and start there.
