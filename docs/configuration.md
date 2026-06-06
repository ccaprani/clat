# Configuration

`clat` reads its configuration from a TOML file. Two settings control
everything: the **threshold** and each rule's **weight**.

!!! note "Config tunes existing rules — it doesn't add new ones"
    Editing `.clat.toml` adjusts the weight of clat's [built-in
    rules](rules.md) and the threshold; it can't introduce a rule that doesn't
    already exist. Got an idea for a rule that isn't there? See [Suggesting a
    new rule](rules.md#suggesting-a-new-rule).

## Where config is read from

clat looks in this order and uses the first file it finds:

1. The path given with `--config <path>`
2. `.clat.toml` in the current working directory
3. `~/.config/clat/config.toml`

If none exists, built-in defaults are used (threshold `5`, each rule at its
default weight).

## Create a config file

```bash
clat set --init
```

This writes a `.clat.toml` in the current directory listing every rule with
its default weight:

```toml
# clat configuration
# Adjust threshold and per-rule weights to taste.
#
# Categories are determined at runtime:
#   clang:  weight >= threshold AND fixable     (auto-fixed)
#   clunk:  weight >= threshold AND NOT fixable  (needs your attention)
#   splat:  weight <  threshold                  (advisory)

threshold = 5

[weights]
labels_inline         =  8  # Merge \label onto the same line as \section (fixable)
decorative_comments   =  6  # Strip decorative comment separators (fixable)
heading_spacing       =  7  # Two blank lines before headings, none after (fixable)
# ... all 17 rules listed
```

`clat set --init` refuses to overwrite an existing `.clat.toml`. To start over,
use `clat set --reset`.

## The threshold

The threshold is the single dial that decides how loud clat is. Each rule's
weight is compared against it:

```text
weight >= threshold  AND fixable      ->  clang  (auto-fixed)
weight >= threshold  AND NOT fixable  ->  clunk  (needs your attention)
weight <  threshold                   ->  splat  (advisory)
```

Lower the threshold to make more rules fire loudly; raise it so only your
highest-priority rules do.

```bash
clat set --threshold 8
```

!!! note "Fixable rules below the threshold still apply"
    A fixable rule under the threshold **still rewrites your text** — it is
    simply reported as a quiet splat instead of a clang. The threshold tunes
    reporting *noise*, not whether safe fixes happen. Setting a fixable rule's
    weight below the threshold demotes it to a (still-applied) splat, not off.

## Set a rule weight

By rule number (see `clat list` for the numbers):

```bash
clat set 12 9     # set rule 12 (ellipsis) to weight 9
clat set 14 2     # demote rule 14 (long_file) to a splat
```

Or edit `.clat.toml` directly under `[weights]`, keyed by the rule's **id**:

```toml
[weights]
ellipsis  = 9
long_file = 2
```

Weights run **1–10**. A weight at or above the threshold promotes a rule to a
clang (fixable) or clunk (detect-only); below the threshold it becomes a
splat.

## Reset to defaults

```bash
clat set --reset
```

## Target a specific file

All `set` and `list` commands accept `--config` to operate on a file other than
`./.clat.toml`:

```bash
clat set --config ~/.config/clat/config.toml --threshold 7
clat list --config ~/.config/clat/config.toml
```

## One-shot overrides

To change the threshold for a single run without editing any file:

```bash
clat --threshold 3 main.tex
```

This affects only that invocation.
