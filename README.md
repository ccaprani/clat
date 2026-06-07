<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/ccaprani/clat/main/docs/assets/wordmark-dark.png">
    <img src="https://raw.githubusercontent.com/ccaprani/clat/main/docs/assets/wordmark-light.png" width="340" alt="clat — Opinionated LaTeX Tidy">
  </picture>
</p>

<p align="center">
  <a href="https://pypi.org/project/clat-tidy/"><img src="https://img.shields.io/pypi/v/clat-tidy?color=3949ab" alt="PyPI"></a>
  <a href="https://pypi.org/project/clat-tidy/"><img src="https://img.shields.io/badge/python-3.8%2B-blue" alt="Python versions"></a>
  <a href="https://ccaprani.github.io/clat/"><img src="https://github.com/ccaprani/clat/actions/workflows/docs.yml/badge.svg" alt="Docs"></a>
  <a href="https://github.com/ccaprani/clat/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="License: MIT"></a>
</p>

<p align="center">
  <em>Colin's LaTeX Tidy — somewhere between a clang and a splat.</em><br>
  📖 <a href="https://ccaprani.github.io/clat/">Documentation</a>
</p>

A configurable LaTeX source formatter with opinions.
Every rule has a weight; you set a threshold.
A weight of `0` disables a rule. What happens otherwise depends on the
combination:

- **clang** -- weight >= threshold *and* fixable: auto-fixed
- **clunk** -- weight >= threshold *and* not fixable: needs your attention
- **splat** -- 0 < weight < threshold: advisory, take it or leave it
- **off** -- weight <= 0: disabled

## Why "clat"?

Prosaically, `clat` is Colin's LaTeX Tool. But the name also has a bit of
printer's noise in it.

In the "Aeolus" episode of *Ulysses* -- "How a great daily organ is turned
out" -- Bloom moves through the newspaper office amid the machinery of print:
clanking, rhythmic, three-four time; thump, thump, thump. My
great-great-grandfather, a Dublin printer, is mentioned there too, though some
editions mangle *Caprani* as *Cuprani*.

So `clat` is meant to sound a little like that composing-room racket: a small,
opinionated machine for turning untidy copy into clean type.

## How clat compares

The usual LaTeX formatting tools —
[latexindent](https://ctan.org/pkg/latexindent),
[tex-fmt](https://github.com/wgunderwood/tex-fmt),
[prettier-plugin-latex](https://github.com/siefkenj/prettier-plugin-latex) —
are excellent at **indentation and line wrapping**. They normalise whitespace,
align tables, and keep columns tidy.

clat operates at a different layer. It doesn't touch indentation. Instead, it
applies **content-aware style rules** that those tools don't cover:

| What you need                          | Tool               |
|----------------------------------------|--------------------|
| Indentation, line wrapping, alignment  | latexindent, tex-fmt |
| Style conventions and writing hygiene  | **clat**           |

For example, clat can:

- Merge stray `\label`s onto their `\section` lines
- Split prose to one sentence per line
- Replace `{\bf text}` with `\textbf{text}`
- Configure inline and display math delimiter preferences separately
- Ensure `~` before `\ref`, `\cite`, and similar commands
- Replace `...` with `\dots`
- Normalise number-unit spacing (`100\,kN`)
- Detect hardcoded references (`Figure 3` instead of `\cref{...}`)
- Add trailing punctuation to display equations
- Convert superscript ordinals (`1\textsuperscript{st}` → `1st`)
- And more

None of these are available in latexindent, tex-fmt, or prettier-plugin-latex.
clat is **complementary** — you can (and should) run both. A typical pipeline:

```bash
tex-fmt main.tex    # indentation, line wrapping
clat main.tex       # style rules
```

The weight/threshold system (clang/clunk/splat/off) also gives you granular
control over which rules auto-fix, which flag for manual review, which are just
advisory noise, and which are disabled — something the existing tools don't
offer.

## Install

```
pip install clat-tidy
```

The command is `clat`. (The distribution is published as `clat-tidy` because
`clat` was already taken on PyPI; everything you type is still `clat`.)

For local development:

```
pip install -e .
```

Requires Python >= 3.8. On Python < 3.11, `tomli` is installed automatically.

## Quick start

```bash
# Format files in place
clat main.tex appendix.tex

# Format a multi-file document by following LaTeX inputs/includes
clat -r main.tex

# Dry run (report without fixing)
clat --check main.tex

# Dry run a multi-file document
clat --check -r main.tex

# List all rules
clat list

# Override threshold for one run
clat --threshold 3 main.tex

# Limit formatting to a single pass instead of fixed-point sweeps
clat --max-iter 1 main.tex
```

## Rules

Run `clat list` to see all rules with their numbers, weights, and current category.

| #  | Rule                  | Default | Fixable | Description                                                |
|----|:----------------------|:-------:|:-------:|------------------------------------------------------------|
|  1 | labels_inline         |    8    |   yes   | Merge `\label` onto the same line as `\section`            |
|  2 | decorative_comments   |    6    |   yes   | Strip decorative comment separators (`%%===` etc.)         |
|  3 | heading_spacing       |    7    |   yes   | Two blank lines before headings, none after                |
|  4 | equation_separators   |    7    |   yes   | Insert `%` lines around display-math environments          |
|  5 | equation_punctuation  |    6    |   yes   | Add trailing comma or period to display equations          |
|  6 | float_indentation     |    5    |   yes   | Tab-indent content inside figure/table/list environments   |
|  7 | one_sentence_per_line |    8    |   yes   | Split sentences onto individual lines                      |
|  8 | math_delimiters_inline  |    5    |   yes   | Replace `\(...\)` with `$...$`                         |
|  9 | tilde_before_refs        |    7    |   yes   | Ensure `~` before `\ref`, `\cite` etc.                  |
| 10 | number_unit_spacing      |    6    |   yes   | Normalise number-unit spacing (`100\,kN`)               |
| 11 | old_font_commands        |    5    |   yes   | Replace `{\bf text}` with `\textbf{text}` etc.          |
| 12 | ellipsis                 |    4    |   yes   | Replace `...` with `\dots`                              |
| 13 | ordinal_suffixes         |    8    |   yes   | Convert superscript ordinals to plain text (`1st`, `2nd`)|
| 14 | long_file                |    3    |   no    | Warn if file exceeds 2000 lines                         |
| 15 | hardcoded_refs           |    6    |   no    | Detect `Figure 3` instead of `\cref{...}`               |
| 16 | manual_sizing            |    3    |   no    | Detect `\big`, `\Big` etc.                              |
| 17 | float_after_heading      |    4    |   no    | Detect float placed directly after a heading            |
| 18 | math_delimiters_display |    0    |   yes   | Replace `\[...\]` with `$$...$$`                       |
| 19 | math_delimiters_equation |    0    |   yes   | Replace `\[...\]` or `$$...$$` with `equation`          |

## Configuration

Config is read from `.clat.toml` in the project directory, falling back to
`~/.config/clat/config.toml`.

### Create a config file

```bash
clat set --init
```

This generates `.clat.toml` with all rules and their default weights:

```toml
threshold = 5

[weights]
labels_inline         =  8  # Merge \label onto the same line as \section (fixable)
decorative_comments   =  6  # Strip decorative comment separators (fixable)
heading_spacing       =  7  # Two blank lines before headings, none after (fixable)
# ... all 19 rules listed
```

Edit the file directly, or use the CLI:

### Set threshold

```bash
clat set --threshold 8
```

### Set a rule weight

```bash
# By rule number (see clat list)
clat set 12 9     # set rule 12 (ellipsis) to weight 9
clat set 15 2     # demote hardcoded refs to a splat
clat set 18 5     # enable display math delimiter conversion
clat set 19 5     # convert display math delimiters to equation environments
```

### Reset to defaults

```bash
clat set --reset
```

### One-shot overrides

Override threshold for a single run without modifying the config:

```bash
clat --threshold 3 main.tex
```

## CLI reference

```
clat <files...>              Format .tex files in place
clat -r <root.tex...>        Recursively format LaTeX inputs/includes
clat --recursive <root.tex>  Long form of -r
clat --check <files...>      Dry run: report issues without fixing
clat --check -r <root.tex>   Dry run a multi-file document
clat -o out.tex in.tex       Write to a different file
clat --threshold N <files>   Override threshold for this run
clat --max-iter N <files>    Maximum fixable-rule sweeps (default 5)

clat list                    List all rules with weights and categories
clat list --config path      Use a specific config file

clat set <rule#> <weight>    Set a rule weight in .clat.toml (0 disables)
clat set --threshold N       Set the threshold in .clat.toml
clat set --init              Create .clat.toml with defaults
clat set --reset             Restore .clat.toml to defaults
clat set --config path       Target a specific config file

clat --version               Show version
```

## Multi-file documents

Use `-r` or `--recursive` when a root `.tex` file assembles a document from
other source files:

```bash
clat -r main.tex
```

Recursive mode follows `\input`, `\include`, `\subfile`, `\import`,
`\subimport`, `\includefrom`, and `\subincludefrom` commands. Paths are
resolved relative to the file containing the command, `.tex` is appended when
no extension is given, duplicate files are skipped, and missing `.tex` inputs
are reported through the normal formatter output.

## How it works

Each rule is either **fixable** (clat can rewrite the source) or **unfixable**
(clat can only detect the issue). clat applies enabled fixable rules repeatedly
until a full sweep makes no text changes, up to `--max-iter` sweeps (default
`5`). Then detect-only rules run once on the final text. At runtime, each rule's
weight is compared to the threshold:

```
weight >= threshold + fixable     =>  clang (auto-fixed)
weight >= threshold + NOT fixable =>  clunk (needs manual fix)
0 < weight < threshold            =>  splat (advisory)
weight <= 0                       =>  off (disabled)
```

Fixable rules below threshold are still applied (the text is still fixed),
but reported as splats rather than clangs. Set a rule's weight to `0` to
disable it entirely. Use `--max-iter 1` for legacy single-pass behaviour.

## Development

```bash
pip install -e .
python -m pytest tests/ -v
```

## License

MIT
