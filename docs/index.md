# clat

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

Every rule has a **weight** (1–10). You set a single **threshold**. What
happens to a given rule depends on the combination of its weight, the
threshold, and whether the rule is auto-fixable:

| Outcome   | Condition                                | Meaning                          |
|-----------|------------------------------------------|----------------------------------|
| **clang** | weight ≥ threshold *and* fixable         | auto-fixed in place              |
| **clunk** | weight ≥ threshold *and* not fixable     | needs your attention            |
| **splat** | weight < threshold                       | advisory — take it or leave it   |

!!! note "Fixable splats are still fixed"
    A fixable rule that falls *below* the threshold still rewrites the text —
    it's just reported as a quiet **splat** rather than a loud **clang**. The
    threshold controls how much noise clat makes, not whether safe fixes
    happen.

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

## Where to next

<div class="grid cards" markdown>

-   :material-download: **[Installation](installation.md)**

    Install from PyPI or set up a development checkout.

-   :material-rocket-launch: **[Quick start](quickstart.md)**

    Format your first file and read a clat report.

-   :material-format-list-numbered: **[Rules](rules.md)**

    All 17 rules, what each does, and before/after examples.

-   :material-cog: **[Configuration](configuration.md)**

    Tune weights and the threshold via `.clat.toml`.

-   :material-console: **[CLI reference](cli.md)**

    Every command and flag.

-   :material-language-python: **[Python API](api.md)**

    Call clat from your own scripts.

</div>
