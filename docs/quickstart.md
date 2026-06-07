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

Enabled fixable rules are applied repeatedly until the text stops changing
(default: up to 5 sweeps), and clat prints a short report of what it did. The
threshold controls whether fixes are reported as clangs or quieter splats;
weight `0` disables a rule.

## Format a whole document

If your document is split across files with `\input` and `\include`, point clat
at the root file with `-r` and it will follow those references and format every
`.tex` file in the tree:

```bash
clat -r main.tex
```

See [Multi-file documents](multi-file.md) for the details.

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
clat v0.5.0  …
  threshold = 5

  ✓  1: clang  w=8   labels_inline
  ✓  2: splat  w=6   decorative_comments
  …
  ✗ 17: clunk  w=6   hardcoded_refs
  …
```

A `✓` marks a fixable rule, `✗` an unfixable (detect-only) one. The middle
column is the live category — **clang**, **clunk**, **splat**, or **off** — given
your threshold.

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
- **off** rules have weight `0` and are skipped entirely.

If there are any clunks or splats, `clat` exits with status **1**, so it slots
neatly into scripts and CI.

## Tune it for one run

Override the threshold for a single invocation without touching your config:

```bash
clat --threshold 3 main.tex   # more rules become clangs/clunks
clat --threshold 9 main.tex   # only the highest-weight rules fire loudly
```

To make a change stick, see [Configuration](configuration.md).

## Limit rule sweeps

By default clat sweeps enabled fixable rules until a full pass makes no text
changes, up to 5 iterations. This helps interacting rules compose cleanly. To
use a single-pass run:

```bash
clat --max-iter 1 main.tex
```

If clat reaches the iteration limit before convergence, it reports a clunk-style
warning so you can spot possible rule interactions.
