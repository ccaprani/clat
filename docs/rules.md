# Rules

`clat` ships with **17 rules** — 13 that it can auto-fix and 4 detect-only
checks. Run `clat list` to see them all with their current weights and
categories.

| #  | Rule                  | Default | Fixable | Description                                                |
|----|:----------------------|:-------:|:-------:|------------------------------------------------------------|
|  1 | `labels_inline`         |    8    |   ✓   | Merge `\label` onto the same line as `\section`             |
|  2 | `decorative_comments`   |    6    |   ✓   | Strip decorative comment separators (`%%===` etc.)         |
|  3 | `heading_spacing`       |    7    |   ✓   | Two blank lines before headings, none after                |
|  4 | `equation_separators`   |    7    |   ✓   | `%` lines around display math; blank lines around floats    |
|  5 | `equation_punctuation`  |    6    |   ✓   | Add trailing comma or period to display equations          |
|  6 | `float_indentation`     |    5    |   ✓   | Tab-indent content inside figure/table/list environments   |
|  7 | `one_sentence_per_line` |    8    |   ✓   | Split sentences onto individual lines                       |
|  8 | `math_delimiters`       |    5    |   ✓   | Replace `\(...\)` with `$...$` and `\[...\]` with `$$...$$` |
|  9 | `tilde_before_refs`     |    7    |   ✓   | Ensure `~` before `\ref`, `\cite` etc.                     |
| 10 | `number_unit_spacing`   |    6    |   ✓   | Normalise number–unit spacing (`100\,kN`)                  |
| 11 | `old_font_commands`     |    5    |   ✓   | Replace `{\bf text}` with `\textbf{text}` etc.            |
| 12 | `ellipsis`              |    4    |   ✓   | Replace `...` with `\dots`                                 |
| 13 | `ordinal_suffixes`      |    8    |   ✓   | Convert superscript ordinals to plain text (`1st`, `2nd`)  |
| 14 | `long_file`             |    3    |   ✗   | Warn if a file exceeds 2000 lines                          |
| 15 | `hardcoded_refs`        |    6    |   ✗   | Detect `Figure 3` instead of `\cref{...}`                 |
| 16 | `manual_sizing`         |    3    |   ✗   | Detect `\big`, `\Big` etc.                                |
| 17 | `float_after_heading`   |    4    |   ✗   | Detect a float placed directly after a heading             |

!!! tip "Order matters"
    Fixable rules are applied in a fixed sequence (decorative comments are
    stripped before sentences are split, labels are merged before heading
    spacing is computed, and so on) so the fixes compose cleanly.

---

## Fixable rules

### 1 · `labels_inline`

Merge a `\label` that sits on the line after a heading onto the same line.

```latex
% before
\section{Introduction}
\label{sec:intro}

% after
\section{Introduction}\label{sec:intro}
```

### 2 · `decorative_comments`

Remove decorative comment separator lines made of repeated `=`, `-`, `*`, `~`,
`#`, or `+`.

```latex
% before
%%==============================
\section{Method}

% after
\section{Method}
```

### 3 · `heading_spacing`

Two blank lines before each heading and none after, so sections breathe.
Consecutive headings (e.g. a `\section` immediately followed by a
`\subsection`) are kept tight, with no blank line between them.

### 4 · `equation_separators`

Set display-math environments off from the surrounding prose with a literal
`%` line above and below, and surround floats (`figure`, `table`) with blank
lines.

```latex
% before
Some prose.
\begin{equation}
    a = b + c
\end{equation}
More prose.

% after
Some prose.
%
\begin{equation}
    a = b + c
\end{equation}
%
More prose.
```

Wrapper environments such as `subequations` receive the separators; the nested
`align`/`equation` inside them do not.

### 5 · `equation_punctuation`

Add a trailing comma or period to a display equation, chosen from the prose
that follows it: a sentence continuation (lower-case start, or a connective
like *where*, *with*, *such that*) gets a comma; a new sentence gets a period.
Existing punctuation is left alone, and the mark is inserted *before* any
trailing `\label`, `\\`, `\nonumber`, or `\notag`.

```latex
% before
\begin{equation}
    F = m a
\end{equation}
where $m$ is the mass.

% after
\begin{equation}
    F = m a,
\end{equation}
where $m$ is the mass.
```

### 6 · `float_indentation`

Tab-indent the content inside `figure`, `table`, `itemize`, and `enumerate`
environments (nesting-aware).

```latex
% before
\begin{figure}
\centering
\includegraphics{plot}
\end{figure}

% after
\begin{figure}
	\centering
	\includegraphics{plot}
\end{figure}
```

### 7 · `one_sentence_per_line`

Put each sentence on its own line — kinder to version control and review
diffs. Abbreviations (`e.g.`, `i.e.`, `Fig.`, `et al.`, …) are protected so
they don't trigger a split, and math, tables, and preamble lines are left
untouched.

```latex
% before
This is one sentence. This is another. And a third.

% after
This is one sentence.
This is another.
And a third.
```

### 8 · `math_delimiters`

Replace the verbose LaTeX2e math delimiters with the short dollar form.

```latex
% before
inline \(x = 1\) and display \[ y = 2 \]

% after
inline $x = 1$ and display $$ y = 2 $$
```

Comment lines and `verbatim` blocks are skipped.

### 9 · `tilde_before_refs`

Insert a non-breaking space (`~`) before `\ref`, `\cref`, `\Cref`, `\eqref`,
and `\cite` so references never wrap onto a new line away from their number.

```latex
% before
as shown in \cref{fig:setup} and \cite{smith2020}

% after
as shown in~\cref{fig:setup} and~\cite{smith2020}
```

### 10 · `number_unit_spacing`

Normalise the space between a number and its unit to a non-expanding thin
space `\,`. Handles ordinary spaces, non-breaking spaces, LaTeX spacing
commands, and missing spaces, for both bare numbers and inline-math values.

```latex
% before
100 kN, 100kN, 100~kN, $78$ MPa, $EI = 200$MN

% after
100\,kN, 100\,kN, 100\,kN, $78$\,MPa, $EI = 200$\,MN
```

A bare `s` is deliberately excluded from the no-space fix so that decades like
`1990s` are not mistaken for units.

### 11 · `old_font_commands`

Replace the old TeX font-switch groups with their LaTeX2e command forms:

| Old        | New              |   | Old        | New             |
|------------|------------------|---|------------|-----------------|
| `{\bf …}`  | `\textbf{…}`     |   | `{\tt …}`  | `\texttt{…}`    |
| `{\it …}`  | `\textit{…}`     |   | `{\sc …}`  | `\textsc{…}`    |
| `{\rm …}`  | `\textrm{…}`     |   | `{\em …}`  | `\emph{…}`      |
| `{\sf …}`  | `\textsf{…}`     |   | `{\sl …}`  | `\textsl{…}`    |

### 12 · `ellipsis`

Replace a literal `...` with `\dots` (skipping comments and `verbatim`/
`lstlisting` blocks).

```latex
% before
and so on...

% after
and so on\dots
```

### 13 · `ordinal_suffixes`

Convert superscript ordinal suffixes to plain text, the typographic
convention in running prose.

```latex
% before
the $1^{st}$ and 2\textsuperscript{nd} cases

% after
the 1st and 2nd cases
```

---

## Detect-only rules

These rules cannot be auto-fixed. Above the threshold they are reported as
**clunks** (needs your attention); below it, as **splats**.

### 14 · `long_file`

Warn when a file exceeds **2000 lines** — a nudge to split it up with
`\input`.

### 15 · `hardcoded_refs`

Flag hardcoded cross-references such as `Figure 3`, `Table 2`, or `Eq. 5`,
which should usually be `\cref{...}` so numbering stays automatic. References
already inside `\ref{`/`\cref{`/`\Cref{` are ignored.

### 16 · `manual_sizing`

Flag manual delimiter sizing — `\big`, `\Big`, `\bigg`, `\Bigg` — where
`\left`/`\right` is usually preferable.

### 17 · `float_after_heading`

Flag a `figure`, `table`, or `algorithm` placed directly after a heading
(allowing only blank lines, `%` comments, and a `\label` in between), and
suggest moving it after some introductory text.

---

## Changing rule behaviour

Every rule's weight is configurable, which moves it between the clang / clunk /
splat categories — or, at weight `0` relative to a high threshold, effectively
mutes it. See [Configuration](configuration.md).

!!! info "Configuration tunes the built-in rules; it doesn't add new ones"
    `.clat.toml` only adjusts the **weight** of the rules listed above and the
    **threshold**. The set of rules itself is fixed in code — there's no way to
    define a brand-new rule from a config file.

## Suggesting a new rule

This list is meant to grow. If there's a tidy-up you'd like clat to make — or a
problem you'd like it to catch — that isn't covered above, please **suggest it**:

- :material-github: Open an issue at
  [github.com/ccaprani/clat/issues](https://github.com/ccaprani/clat/issues).

A good rule suggestion includes:

- **What it should do** — a one-line description, the way the table above reads.
- **A before/after example** (for a fixable rule) or an example of what should
  be **flagged** (for a detect-only rule).
- **Whether it's auto-fixable** — can the change be made unambiguously, or can
  clat only point at the problem?
- **Edge cases** it should *not* touch (verbatim blocks, comments, math, …).

Pull requests are welcome too — each rule is a small function in
`src/clat/rules.py` registered in the `RULES` list, with tests in
`tests/test_rules.py`. The [Python API](api.md) page documents the `Rule`
structure.
