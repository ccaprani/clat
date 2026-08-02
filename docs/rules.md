# Rules

`clat` ships with **22 rules** — 18 that it can auto-fix and 4 detect-only
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
|  8 | `math_delimiters_inline`   |    5    |   ✓   | Replace `\(...\)` with `$...$`                       |
|  9 | `math_delimiters_display`  |    0    |   ✓   | Replace `\[...\]` with `$$...$$`                    |
| 10 | `math_delimiters_equation` |    0    |   ✓   | Replace `\[...\]` or `$$...$$` with `equation`      |
| 11 | `tilde_before_refs`        |    7    |   ✓   | Ensure `~` before `\ref`, `\cite` etc.               |
| 12 | `number_unit_spacing`      |    6    |   ✓   | Normalise number–unit spacing (`100\,kN`)             |
| 13 | `old_font_commands`        |    5    |   ✓   | Replace `{\bf text}` with `\textbf{text}` etc.       |
| 14 | `ellipsis`                 |    4    |   ✓   | Replace `...` with `\dots`                            |
| 15 | `ordinal_suffixes`         |    8    |   ✓   | Convert superscript ordinals to plain text (`1st`, `2nd`)|
| 16 | `table_line_endings`       |    7    |   ✓   | Keep table `\\` on row lines and rules on own lines   |
| 17 | `abbreviation_spacing`     |    7    |   ✓   | Force interword space after `e.g.`, `i.e.`, `et al.`  |
| 22 | `join_wrapped_lines`       |    8    |   ✓   | Join hard-wrapped lines so each sentence is one line   |
| 18 | `long_file`                |    3    |   ✗   | Warn if a file exceeds 2000 lines                      |
| 19 | `hardcoded_refs`           |    6    |   ✗   | Detect `Figure 3` instead of `\cref{...}`             |
| 20 | `manual_sizing`            |    3    |   ✗   | Detect `\big`, `\Big` etc.                           |
| 21 | `float_after_heading`      |    4    |   ✗   | Detect a float placed directly after a heading         |

!!! tip "Order still matters, but sweeps help"
    Fixable rules are applied in a fixed sequence (decorative comments are
    stripped before sentences are split, labels are merged before heading
    spacing is computed, and so on). clat then repeats that sequence until a
    full sweep makes no text changes, up to `--max-iter` iterations, so
    interacting rules can settle to a fixed point.

!!! note "Picture environments are protected"
    Every rule below skips the contents of **protected environments** — TikZ,
    pgfplots, and tikz-cd by default — so coordinates, node text, and lengths
    are never mangled. You can change which environments are protected, or let
    a specific rule back in, via
    [`protected_environments` / `unprotected_rules`](configuration.md#protected-environments).

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
untouched. Caption bodies are treated as prose too: continuation sentences use
the same indentation as their `\caption` command.

```latex
% before
This is one sentence. This is another. And a third.

% after
This is one sentence.
This is another.
And a third.
```

### 8 · `math_delimiters_inline`

Replace the verbose LaTeX2e inline math delimiters with the short dollar form.
Display delimiter style is handled separately by Rules 9 and 10 so users can
weight each preference independently.

```latex
% before
inline \(x = 1\)

% after
inline $x = 1$
```

Comment lines and verbatim starts are skipped.

### 9 · `math_delimiters_display`

Replace display math delimiters `\[...\]` with `$$...$$`. It is disabled by
default because many LaTeX users prefer `\[...\]`.

```latex
% before
\[ y = 2 \]

% after
$$ y = 2 $$
```

If you prefer `$$...$$`, set this rule's weight above `0` to enable it while
keeping Rule 8 for inline math delimiters independent.

### 10 · `math_delimiters_equation`

Replace standalone display math delimiter blocks (`\[...\]` or `$$...$$`) with
an `equation` environment. It is disabled by default because display-math
delimiter style is especially user- and journal-dependent.

```latex
% before
\[
    y = 2
\]

% after
\begin{equation}
    y = 2
\end{equation}
```

Only standalone display-math blocks are converted; inline prose such as
`before \[x\] after` is left alone. Comments and verbatim/listing blocks are
skipped. Because the result is an `equation` environment, the existing equation
spacing and punctuation rules may then apply as usual.

### 11 · `tilde_before_refs`

Insert a non-breaking space (`~`) before `\ref`, `\cref`, `\Cref`, `\eqref`,
and `\cite` so references never wrap onto a new line away from their number.

```latex
% before
as shown in \cref{fig:setup} and \cite{smith2020}

% after
as shown in~\cref{fig:setup} and~\cite{smith2020}
```

### 12 · `number_unit_spacing`

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

Only the **document body** is touched. A number and unit are a TeX dimension —
not prose — in the preamble, and after a `=` or `[` anywhere (`margin=25mm`,
`\includegraphics[width=100mm]`, row spacing `\\[10mm]`); there `\,` would be
invalid, so those are left alone. Units inside a text-mode argument such as
`\textbf{100 kN}` are still spaced.

### 13 · `old_font_commands`

Replace the old TeX font-switch groups with their LaTeX2e command forms:

| Old        | New              |   | Old        | New             |
|------------|------------------|---|------------|-----------------|
| `{\bf …}`  | `\textbf{…}`     |   | `{\tt …}`  | `\texttt{…}`    |
| `{\it …}`  | `\textit{…}`     |   | `{\sc …}`  | `\textsc{…}`    |
| `{\rm …}`  | `\textrm{…}`     |   | `{\em …}`  | `\emph{…}`      |
| `{\sf …}`  | `\textsf{…}`     |   | `{\sl …}`  | `\textsl{…}`    |

### 14 · `ellipsis`

Replace a literal `...` with `\dots` (skipping comments and `verbatim`/
`lstlisting` blocks).

```latex
% before
and so on...

% after
and so on\dots
```

### 15 · `ordinal_suffixes`

Convert superscript ordinal suffixes to plain text, the typographic
convention in running prose.

```latex
% before
the $1^{st}$ and 2\textsuperscript{nd} cases

% after
the 1st and 2nd cases
```

### 16 · `table_line_endings`

Keep table row endings (`\\`) on the same line as the row content, and keep
horizontal rules (`\hline`, `\toprule`, `\midrule`, `\bottomrule`) on their
own lines.

```latex
% before
\hline
$I_b$ & 0.509
\\
$A$ & 1 \\ \hline

% after
\hline
$I_b$ & 0.509 \\
$A$ & 1 \\
\hline
```

### 17 · `abbreviation_spacing`

After abbreviations such as `e.g.`, `i.e.` or `et al.`, the trailing period
reads to TeX as a full stop, so it inserts a wider end-of-sentence space.
Replacing the following space with a control space (`\ `) keeps it an ordinary
interword space (one that still stretches a little).

`e.g.`, `i.e.`, `cf.`, `viz.` and `vs.` never end a sentence, so they are fixed
whatever follows. `et al.` and `etc.` can end a sentence, so they are only fixed
before a clear continuation — a lowercase letter, a digit, or an opening
parenthesis — leaving a following capital alone as a possible full stop.

```latex
% before
Use a tool, e.g. clat. Reported by Smith et al. (2020).

% after
Use a tool, e.g.\ clat. Reported by Smith et al.\ (2020).
```

### 22 · `join_wrapped_lines`

The inverse of [Rule 7 (`one_sentence_per_line`)](#7-one_sentence_per_line):
where that rule *splits* a line carrying several sentences, this one *joins* a
sentence that has been hard-wrapped across several lines. With both enabled,
prose settles to exactly one sentence per line — even when the source arrives
wrapped at a fixed column (as an editor or `fmt` leaves it), which Rule 7 alone
cannot repair because it never joins lines.

```latex
% before
Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do
eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim
ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut
aliquip ex ea commodo consequat.

% after
Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
```

A line is joined onto the current one unless the current one already ends a
sentence — a terminal `.`, `?`, or `!` after abbreviation protection (`Fig.`,
`e.g.`, …) and any trailing math, quote, or bracket closers, so a sentence
ending inside `$$…$$` or `\emph{…}` is still recognised. Blank lines, comments,
protected environments (`equation`, `table`, `figure`, `verbatim`,
…), and structural commands are boundaries. A float body remains protected
except for its `\caption` body, which is rejoined here and then split by Rule 7
so that it also settles to one sentence per line. An `\item` starts a fresh run,
so its wrapped body is gathered without being pulled onto the line above; a
heading whose title is wrapped across lines is rejoined into a single line rather
than spilling into the following prose.

---

## Detect-only rules

These rules cannot be auto-fixed. Above the threshold they are reported as
**clunks** (needs your attention); below it, as **splats**. At weight `0`, they
are skipped entirely.

### 18 · `long_file`

Warn when a file exceeds **2000 lines** — a nudge to split it up with
`\input`.

### 19 · `hardcoded_refs`

Flag hardcoded cross-references such as `Figure 3`, `Table 2`, or `Eq. 5`,
which should usually be `\cref{...}` so numbering stays automatic. References
already inside `\ref{`/`\cref{`/`\Cref{` are ignored.

### 20 · `manual_sizing`

Flag manual delimiter sizing — `\big`, `\Big`, `\bigg`, `\Bigg` — where
`\left`/`\right` is usually preferable.

### 21 · `float_after_heading`

Flag a `figure`, `table`, or `algorithm` placed directly after a heading
(allowing only blank lines, `%` comments, and a `\label` in between), and
suggest moving it after some introductory text.

---

## Changing rule behaviour

Every rule's weight is configurable, which moves it between the clang / clunk /
splat categories. Set a rule's weight to `0` to disable it entirely. See
[Configuration](configuration.md).

!!! info "Configuration tunes built-in rules by id; it doesn't add new ones"
    `.clat.toml` adjusts the **weight** of rules by their ids and the
    **threshold**. Rule numbers are list references for `clat list`/`clat set`,
    not config keys. The set of rules itself is fixed in code — there's no way
    to define a brand-new rule from a config file.

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
