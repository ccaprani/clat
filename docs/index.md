# clat

[![PyPI](https://img.shields.io/pypi/v/clat-tidy?color=3949ab)](https://pypi.org/project/clat-tidy/)
[![Python versions](https://img.shields.io/badge/python-3.8%2B-blue)](https://pypi.org/project/clat-tidy/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](https://github.com/ccaprani/clat/blob/main/LICENSE)

**Colin's LaTeX Tidy** — somewhere between a clang and a splat.

`clat` is a configurable LaTeX source formatter with opinions. It cleans up
untidy `.tex` files: merging stray `\label`s onto their headings, spacing
display math, splitting one sentence per line, normalising units, and a dozen
more transformations — each one you can dial up, dial down, or switch off.

```bash
pip install clat-tidy
clat main.tex
```

The installed command is `clat`. (The PyPI distribution is `clat-tidy` because
`clat` was already taken; everything you type is still `clat`.)

## clang, clunk, splat

Every rule has a **weight** (0–10; 0 disables). You set a single **threshold**. What
happens to a given rule depends on the combination of its weight, the
threshold, and whether the rule is auto-fixable:

| Outcome   | Condition                                | Meaning                          |
|-----------|------------------------------------------|----------------------------------|
| **clang** | weight ≥ threshold *and* fixable         | auto-fixed in place              |
| **clunk** | weight ≥ threshold *and* not fixable     | needs your attention             |
| **splat** | 0 < weight < threshold                   | advisory — take it or leave it   |
| **off**   | weight ≤ 0                               | disabled                         |

!!! note "Fixable splats are still fixed"
    A fixable rule that falls *below* the threshold still rewrites the text —
    it's just reported as a quiet **splat** rather than a loud **clang**. The
    threshold controls how much noise clat makes, not whether safe fixes
    happen. Set a rule's weight to `0` to disable it entirely.

## Why "clat"?

Prosaically, `clat` is Colin's LaTeX Tool. But the name also has a bit of
printer's noise in it.

In the "Aeolus" episode of *Ulysses* — "How a great daily organ is turned
out" — Bloom moves through the newspaper office amid the machinery of print:
clanking, rhythmic, three-four time; thump, thump, thump. My
great-great-grandfather, a Dublin printer, is mentioned there too, though some
editions mangle *Caprani* as *Cuprani*.

So `clat` is meant to sound a little like that composing-room racket: a small,
opinionated machine for turning untidy copy into clean type.

## How clat compares

The usual LaTeX formatting tools — [latexindent][latexindent], [tex-fmt][tex-fmt],
[prettier-plugin-latex][prettier-latex] — are excellent at **indentation and line
wrapping**. They normalise whitespace, align tables, and keep columns tidy.

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

[latexindent]: https://ctan.org/pkg/latexindent
[tex-fmt]: https://github.com/wgunderwood/tex-fmt
[prettier-latex]: https://github.com/siefkenj/prettier-plugin-latex

## Where to next

<div class="grid cards" markdown>

-   :material-download: **[Installation](installation.md)**

    Install from PyPI or set up a development checkout.

-   :material-rocket-launch: **[Quick start](quickstart.md)**

    Format your first file and read a clat report.

-   :material-format-list-numbered: **[Rules](rules.md)**

    All 18 rules, what each does, and before/after examples.

-   :material-cog: **[Configuration](configuration.md)**

    Tune weights and the threshold via `.clat.toml`.

-   :material-console: **[CLI reference](cli.md)**

    Every command and flag.

-   :material-language-python: **[Python API](api.md)**

    Call clat from your own scripts.

</div>
