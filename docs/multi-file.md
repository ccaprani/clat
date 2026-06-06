# Multi-file documents

Real LaTeX projects are rarely a single file. A root `main.tex` typically
assembles the document from chapters, sections, and appendices via `\input`
and `\include`. Pass `-r` (or `--recursive`) and clat formats the whole tree
from the root down:

```bash
clat -r main.tex
```

This works with `--check` too, to dry-run an entire document:

```bash
clat --check -r main.tex
```

## What clat follows

Recursive mode discovers `.tex` files referenced by any of these commands:

| Command form | Example |
|--------------|---------|
| `\input{...}`            | `\input{chapters/intro}` |
| `\input ...` (no braces) | `\input chapters/intro` |
| `\include{...}`          | `\include{chapters/method}` |
| `\subfile{...}`          | `\subfile{appendix/app.tex}` |
| `\import{dir}{file}`     | `\import{sections/}{method}` |
| `\subimport{dir}{file}`  | `\subimport{sections/}{method}` |
| `\includefrom{dir}{file}`| `\includefrom{parts/}{one}` |
| `\subincludefrom{dir}{file}` | `\subincludefrom{parts/}{one}` |

Starred variants (e.g. `\include*`) are recognised as well.

## How paths are resolved

- **Relative to the referencing file.** A path is resolved relative to the
  directory of the file that contains the command — so `\input{../shared/defs}`
  inside `chapters/intro.tex` resolves against `chapters/`. For the
  `\import`-family commands, the first `{dir}` argument is applied first.
- **`.tex` is assumed.** If no extension is given, `.tex` is appended
  (`\input{chapters/intro}` → `chapters/intro.tex`).
- **Only `.tex` is followed.** References to `.sty`, `.bib`, images, or other
  non-source files are ignored — clat only formats LaTeX source.
- **Comments are respected.** A commented-out line such as
  `% \input{old-draft}` is skipped. An escaped percent (`\%`) does not start a
  comment.

## Traversal order and duplicates

- Roots you pass on the command line are visited **in order**.
- Dependencies are followed **depth-first**, in the order they appear in each
  file.
- Each file is formatted **once** — duplicates (including cycles, where two
  files `\input` each other) are de-duplicated, so clat never loops or
  double-formats.

For example, given:

```latex
% main.tex
\input{chapters/intro}
\include{chapters/method}
\subfile{appendix/app.tex}
```

`clat -r main.tex` formats `main.tex`, then `chapters/intro.tex` (and anything
*it* inputs), then `chapters/method.tex`, then `appendix/app.tex`.

## Missing files

If a referenced `.tex` file doesn't exist, clat keeps it in the work list and
reports it through the normal formatter output as a missing file, rather than
failing silently — so a typo'd `\input` path is surfaced, not swallowed.

## Restrictions

`-r` cannot be combined with `-o/--output`: recursive mode rewrites each
discovered file in place (or, with `--check`, rewrites nothing), so there is no
single output file to redirect to.

!!! tip "Discovering files programmatically"
    The same traversal is available from Python as
    [`clat.cli.discover_tex_files`](api.md#clat.cli.discover_tex_files), which
    returns the ordered, de-duplicated list of files clat would format.
