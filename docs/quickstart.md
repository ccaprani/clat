# Quick start

## Format a file

`clat` formats `.tex` files **in place** by default:

```bash
clat main.tex
```

Pass as many files as you like:

```bash
clat main.tex appendix.tex sections/*.tex
```

Each fixable rule whose weight meets the threshold is applied, and clat prints
a short report of what it did.

## Look before you leap

Not ready to rewrite anything? Use `--check` for a dry run. clat reports what
*would* change but leaves your files untouched:

```bash
clat --check main.tex
```

This is what you'd run in CI or a pre-commit hook: it exits non-zero if there
is anything to fix or flag, and zero if the file is already clean.

## Write somewhere else

To leave the input untouched and write the formatted result to a new file
(single input only):

```bash
clat -o main.clean.tex main.tex
```

## See the rules

List every rule with its number, current weight, and resulting category for
your current threshold:

```bash
clat list
```

```text
clat v0.4.0  …
  threshold = 5

  ✓  1: clang  w=8   labels_inline
  ✓  2: splat  w=6   decorative_comments
  …
  ✗ 15: clunk  w=6   hardcoded_refs
  …
```

A `✓` marks a fixable rule, `✗` an unfixable (detect-only) one. The middle
column is the live category — **clang**, **clunk**, or **splat** — given your
threshold.

## Reading a report

A typical run looks like this:

```text
  main.tex: fixed 4 rules (12 times), 1 clunk (2 times), 2 splats (3 times)
    Figure 3 …  main.tex:118: possible hardcoded ref: "Figure 3"
    …
```

- **clangs** are the auto-fixes clat already applied.
- **clunks** are problems clat can detect but can't fix — over to you.
- **splats** are advisory; below your threshold, so reported but low-priority.

If there are any clunks or splats, `clat` exits with status **1**, so it slots
neatly into scripts and CI.

## Tune it for one run

Override the threshold for a single invocation without touching your config:

```bash
clat --threshold 3 main.tex   # more rules become clangs/clunks
clat --threshold 9 main.tex   # only the highest-weight rules fire loudly
```

To make a change stick, see [Configuration](configuration.md).
