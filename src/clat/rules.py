"""
clat formatting rules.

Every rule has a number, a default weight (1–10; 0 disables), and a fixable flag.
At runtime, the user's threshold decides what happens:

  clang:  weight >= threshold AND fixable      → auto-fixed
  clunk:  weight >= threshold AND NOT fixable   → must fix manually
  splat:  0 < weight < threshold                → advisory
  off:    weight <= 0                           → disabled

Run ``clat list`` to see all rules. Configure via ``.clat.toml``
or ``clat set <rule#> <weight>``.
"""

import re
from dataclasses import dataclass, field
from typing import Callable, Optional

# ── Abbreviations for sentence splitting ─────────────────────────────

ABBREVIATIONS = [
    'e.g', 'i.e', 'cf', 'etc', 'vs', 'et al', 'viz', 'ibid',
    'Dr', 'Mr', 'Mrs', 'Ms', 'Prof', 'Sr', 'Jr', 'St',
    'Fig', 'Figs', 'Eq', 'Eqs', 'Ref', 'Refs', 'Sec', 'Secs',
    'Ch', 'Vol', 'vol', 'no', 'No', 'pp', 'ed', 'eds',
    'Proc', 'Trans', 'Rev',
    'approx', 'resp', 'incl',
]

PLACEHOLDER = '\x00'


def _build_protect_pattern():
    abbrs = sorted(ABBREVIATIONS, key=len, reverse=True)
    escaped = [re.escape(a) for a in abbrs]
    pattern = r'(?:' + '|'.join(escaped) + r')\.'
    return re.compile(pattern)


PROTECT_RE = _build_protect_pattern()

CONTINUATION_WORDS = re.compile(
    r'^(?:where|with|for|in\s+which|such\s+that|so\s+that|and|here|'
    r'noting|since|because|if|as|giving|yielding|from\s+which|'
    r'subject\s+to|provided|assuming|respectively)\b',
    re.IGNORECASE,
)

_UNITS = (
    r'm', r'km', r'cm', r'mm', r'µm', r'nm',
    r'kg', r'g', r'mg', r'tonne',
    r's', r'ms', r'µs', r'ns', r'min', r'hr',
    r'N', r'kN', r'MN', r'GN',
    r'Pa', r'kPa', r'MPa', r'GPa',
    r'Hz', r'kHz', r'MHz', r'GHz',
    r'J', r'kJ', r'MJ',
    r'W', r'kW', r'MW',
    r'rad', r'deg',
    r'm/s', r'm/s\$\^2\$', r'm/s\\\^2',
)

_FONT_MAP = {
    'bf': 'textbf', 'it': 'textit', 'rm': 'textrm', 'sf': 'textsf',
    'tt': 'texttt', 'sc': 'textsc', 'em': 'emph', 'sl': 'textsl',
}

# Display-math environments that should be separated from surrounding prose
# by a literal '%' line.  Keep this as a list of environment names rather than
# baking the policy into increasingly broad regular expressions: wrappers such
# as subequations need separators around the wrapper, not around the nested
# align/equation environment inside it.
_MATH_SEPARATOR_ENVS = {
    'equation', 'equation*',
    'align', 'align*',
    'alignat', 'alignat*',
    'gather', 'gather*',
    'multline', 'multline*',
    'flalign', 'flalign*',
    'displaymath',
    'eqnarray', 'eqnarray*',
    'subequations',
}

_FLOAT_SEPARATOR_ENVS = {'figure', 'table'}
_BEGIN_ENV_RE = re.compile(r'^\s*\\begin\{([^}]+)\}')
_END_ENV_RE = re.compile(r'^\s*\\end\{([^}]+)\}')


def _begin_env(line):
    match = _BEGIN_ENV_RE.match(line)
    return match.group(1) if match else None


def _end_env(line):
    match = _END_ENV_RE.match(line)
    return match.group(1) if match else None


def _contains_math_env(env_stack):
    return any(env in _MATH_SEPARATOR_ENVS for env in env_stack)


def _starts_separator_env(line):
    env = _begin_env(line)
    return env in _MATH_SEPARATOR_ENVS or env in _FLOAT_SEPARATOR_ENVS


def _pop_env(env_stack, env):
    for i in range(len(env_stack) - 1, -1, -1):
        if env_stack[i] == env:
            del env_stack[i:]
            return


# ── Rule registry ───────────────────────────────────────────────────

DEFAULT_THRESHOLD = 5


@dataclass
class Rule:
    """A single clat rule.

    Attributes
    ----------
    id : str        — unique key, used in config overrides (e.g. 'labels_inline')
    name : str      — human-readable description
    fn : callable   — fix function  f(text) -> text           (fixable=True)
                       or warn function  f(text, filename) -> [(file, line, msg)]
    weight : int    — default severity 1–10; 0 disables the rule
    fixable : bool  — True if clat can auto-fix this
    order : int     — execution order (lower = earlier); fixes run before warns
    """
    num: int
    id: str
    name: str
    fn: Callable
    weight: int
    fixable: bool
    order: int


# Registry populated after all rule functions are defined (bottom of file).
RULES: list[Rule] = []


# ── Fix rules ────────────────────────────────────────────────────────

def rule1_labels_inline(text):
    """Merge \\label on the line after a heading onto the same line."""
    return re.sub(
        r'(\\(?:sub)*section\*?\{[^}]+\})\s*\n\s*(\\label\{[^}]+\})',
        r'\1\2',
        text,
    )


def rule2_equation_separators(text):
    """% lines around display-math environments; blank lines around floats."""
    lines = text.split('\n')
    result = []
    env_stack = []
    n = len(lines)

    for i, line in enumerate(lines):
        # Clean up separator lines that earlier formatter versions inserted
        # around nested align/equation environments inside wrappers such as
        # subequations.  The wrapper receives the surrounding separators.
        if line.strip() == '%' and _contains_math_env(env_stack):
            continue

        begin_env = _begin_env(line)
        end_env = _end_env(line)
        is_math_start = begin_env in _MATH_SEPARATOR_ENVS
        is_float_start = begin_env in _FLOAT_SEPARATOR_ENVS
        inside_math = _contains_math_env(env_stack)

        if (is_math_start or is_float_start) and result:
            prev = result[-1].strip()
            if is_math_start and not inside_math and prev and prev != '%':
                result.append('%')
            elif is_float_start and prev and prev != '':
                result.append('')

        result.append(line)

        if begin_env:
            env_stack.append(begin_env)

        is_math_end = end_env in _MATH_SEPARATOR_ENVS
        is_float_end = end_env in _FLOAT_SEPARATOR_ENVS
        if end_env:
            _pop_env(env_stack, end_env)

        if (is_math_end or is_float_end) and i + 1 < n:
            nxt = lines[i + 1].strip()
            if (is_math_end and not _contains_math_env(env_stack)
                    and nxt and nxt != '%' and not _starts_separator_env(lines[i + 1])):
                result.append('%')
            elif is_float_end and nxt and nxt != '':
                result.append('')

    return '\n'.join(result)


def rule3_one_sentence_per_line(text):
    """Split sentences onto individual lines, protecting abbreviations."""
    lines = text.split('\n')
    result = []
    skip_re = re.compile(
        r'^\s*(%|\\begin|\\end|\\item|\\paragraph|\\section|\\subsection|'
        r'\\subsubsection|\\caption|\\label|\\centering|\\includegraphics|'
        r'\\toprule|\\midrule|\\bottomrule|\\hline|\\RequirePackage|'
        r'\\usepackage|\\newcommand|\\renewcommand|\\def|\\let|\\input|'
        r'\\bibliography|\\documentclass|\\title|\\author|\\address|'
        r'\\ead|\\cortext|\\journal|\\bibliographystyle|\\addtolength|'
        r'\\Require|\\Ensure|\\Statex|\\State|\\For|\\EndFor|\\If|\\EndIf)'
    )
    in_env = 0
    for line in lines:
        stripped = line.strip()
        if re.match(r'^\s*\\begin\{(equation|align|table|tabular|figure|algorithm|'
                     r'algorithmic|abstract|keyword|frontmatter|verbatim|lstlisting)\}', line):
            in_env += 1
        if re.match(r'^\s*\\end\{(equation|align|table|tabular|figure|algorithm|'
                     r'algorithmic|abstract|keyword|frontmatter|verbatim|lstlisting)\}', line):
            in_env = max(0, in_env - 1)
            result.append(line)
            continue
        if in_env or not stripped or stripped == '%' or skip_re.match(stripped):
            result.append(line)
            continue
        protected = PROTECT_RE.sub(lambda m: m.group(0)[:-1] + PLACEHOLDER, line)
        parts = re.split(r'\.(\s+)(?=[A-Z])', protected)
        sentences = []
        i = 0
        while i < len(parts):
            if i + 1 < len(parts) and re.match(r'^\s+$', parts[i + 1]):
                sentences.append(parts[i] + '.')
                i += 2
            else:
                sentences.append(parts[i])
                i += 1
        for s in sentences:
            restored = s.replace(PLACEHOLDER, '.')
            if restored.strip():
                result.append(restored)
    return '\n'.join(result)


def rule4_equation_punctuation(text):
    """Add trailing comma or period to display equations based on context."""
    lines = text.split('\n')
    env_end = re.compile(r'^\s*\\end\{(equation|align)\}\*?')
    result = list(lines)
    n = len(result)
    for i in range(n):
        if not env_end.match(result[i]):
            continue
        math_line = None
        math_idx = None
        for j in range(i - 1, -1, -1):
            s = result[j].strip()
            if s == '%' or s == '' or s.startswith('\\end{'):
                continue
            if re.match(r'^\\label\{[^}]+\}$', s):
                continue
            math_line = result[j]
            math_idx = j
            break
        if math_idx is None:
            continue
        content = math_line.rstrip()
        bare = re.sub(r'\s*\\label\{[^}]+\}\s*$', '', content)
        bare = re.sub(r'\s*(?:\\\\|\\nonumber|\\notag)\s*$', '', bare)
        bare = re.sub(r'\}$', '', bare) if '\\boxed' in content else bare
        bare = bare.rstrip()
        if bare and bare[-1] in '.,;:':
            continue
        next_prose = None
        for k in range(i + 1, n):
            s = result[k].strip()
            if s == '' or s == '%':
                continue
            next_prose = s
            break
        if next_prose is None:
            punct = '.'
        elif next_prose.startswith('\\begin{'):
            punct = ','
        elif CONTINUATION_WORDS.match(next_prose):
            punct = ','
        elif next_prose[0].islower():
            punct = ','
        elif next_prose[0].isupper():
            punct = '.'
        else:
            continue
        trail_match = re.search(
            r'(\s*(?:\\label\{[^}]+\}|\\\\|\\nonumber|\\notag)\s*)$', content)
        if trail_match:
            ins = trail_match.start()
            result[math_idx] = content[:ins] + punct + content[ins:]
        else:
            result[math_idx] = content + punct
    return '\n'.join(result)


def rule5_heading_spacing(text):
    """Two blank lines before headings, no blank line after."""
    lines = text.split('\n')
    heading_re = re.compile(r'^\s*\\(?:sub)*section\*?\{')
    result = []
    for i, line in enumerate(lines):
        if heading_re.match(line):
            while result and result[-1].strip() == '':
                result.pop()
            if result:
                # No blank lines between consecutive headings
                if not heading_re.match(result[-1]):
                    result.append('')
                    result.append('')
            result.append(line)
            continue
        if i > 0 and line.strip() == '':
            prev_idx = len(result) - 1
            while prev_idx >= 0 and result[prev_idx].strip() == '':
                prev_idx -= 1
            if prev_idx >= 0 and heading_re.match(result[prev_idx]):
                continue
        result.append(line)
    return '\n'.join(result)


def rule6_figure_indentation(text):
    """Tab-indent content inside figure, table, itemize, enumerate environments."""
    lines = text.split('\n')
    result = []
    env_re_open = re.compile(r'^\s*\\begin\{(figure|table|itemize|enumerate)\}')
    env_re_close = re.compile(r'^\s*\\end\{(figure|table|itemize|enumerate)\}')
    depth = 0
    for line in lines:
        stripped = line.strip()
        if depth > 0 and env_re_close.match(line):
            depth -= 1
            result.append('\t' * depth + stripped if depth > 0 else stripped)
            continue
        if depth > 0:
            if not stripped:
                result.append(line)
            elif line.startswith('\t'):
                existing_tabs = len(line) - len(line.lstrip('\t'))
                if existing_tabs < depth:
                    result.append('\t' * depth + line.lstrip('\t'))
                else:
                    result.append(line)
            else:
                leading = len(line) - len(line.lstrip())
                if leading > 0:
                    result.append('\t' * depth + line)
                else:
                    result.append('\t' * depth + stripped)
        else:
            result.append(line)
        if env_re_open.match(line):
            depth += 1
    return '\n'.join(result)


def rule7_strip_decorative_comments(text):
    """Remove decorative comment separator lines."""
    lines = text.split('\n')
    deco_re = re.compile(r'^\s*%+\s*[=\-\*~#+]{4,}\s*$')
    return '\n'.join(line for line in lines if not deco_re.match(line))


def rule8_math_delimiters_inline(text):
    """\\(...\\) -> $...$.

    Converts the verbose LaTeX2e inline math delimiters to the short dollar
    form. Matched within a single line so that an unbalanced ``\\(`` does not
    greedily consume across paragraphs. Comment lines and verbatim starts are
    skipped.
    """
    lines = text.split('\n')
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('%') or stripped.startswith('\\begin{verbatim'):
            result.append(line)
            continue
        result.append(re.sub(r'\\\((.*?)\\\)', r'$\1$', line))
    return '\n'.join(result)


def rule18_math_delimiters_display(text):
    """\\[...\\] -> $$...$$.

    Converts the verbose LaTeX2e display-math delimiters to the short
    double-dollar form. Display math may span lines and is handled with
    DOTALL.
    """
    return re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)


_DISPLAY_TO_EQUATION_RE = re.compile(
    r'(?ms)^(?P<indent>[ \t]*)(?:'
    r'\\\[(?P<bracket>.*?)\\\]|'
    r'\$\$(?P<dollar>.*?)\$\$'
    r')[ \t]*$'
)


def _display_math_to_equation(match):
    indent = match.group('indent')
    content = match.group('bracket')
    if content is None:
        content = match.group('dollar')
    body = content.strip('\n')
    if not (content.startswith('\n') or content.endswith('\n')):
        body = body.strip()
    return f'{indent}\\begin{{equation}}\n{body}\n{indent}\\end{{equation}}'


def _convert_display_math_to_equation_chunk(text):
    return _DISPLAY_TO_EQUATION_RE.sub(_display_math_to_equation, text)


def rule19_math_delimiters_equation(text):
    """\\[...\\] or $$...$$ -> equation environment.

    Only standalone display-math delimiter blocks are converted. Lines that are
    comments, and verbatim/lstlisting blocks, are skipped.
    """
    lines = text.splitlines(keepends=True)
    result = []
    chunk = []
    in_verbatim = False

    def flush_chunk():
        if chunk:
            result.append(_convert_display_math_to_equation_chunk(''.join(chunk)))
            chunk.clear()

    for line in lines:
        stripped = line.strip()
        starts_verbatim = re.match(r'^\\begin\{(verbatim|lstlisting)\}', stripped)
        ends_verbatim = re.match(r'^\\end\{(verbatim|lstlisting)\}', stripped)

        if in_verbatim or starts_verbatim:
            flush_chunk()
            result.append(line)
            in_verbatim = not bool(ends_verbatim)
            continue

        if stripped.startswith('%'):
            flush_chunk()
            result.append(line)
            continue

        chunk.append(line)

    flush_chunk()
    return ''.join(result)


def rule9_tilde_before_refs(text):
    """Ensure ~ before \\ref, \\cref, \\eqref, \\cite."""
    return re.sub(
        r'(?<=[A-Za-z0-9).])\s+(\\(?:c?ref|eqref|cite|Cref)\{)',
        r'~\1', text)


def rule10_number_unit_spacing(text):
    """Normalise number-unit spacing to a non-expanding thin space.

    Handles ordinary spaces, non-breaking spaces, LaTeX spacing commands, and
    missing spaces:
      * ``100 kN``, ``100~kN`` or ``100kN``       -> ``100\\,kN``
      * ``100\\;kN`` or ``100\\quad kN``          -> ``100\\,kN``
      * ``$78$ kN``, ``$78$~kN`` or ``$78$kN``    -> ``$78$\\,kN``
      * ``$EI = 200$ MN`` or ``$EI = 200$MN``     -> ``$EI = 200$\\,MN``

    Already-correct ``\\,`` spacing is left unchanged.  No-space fixes exclude
    bare ``s`` to avoid turning decades such as ``1990s`` into units.
    """
    units = sorted(_UNITS, key=len, reverse=True)
    no_sep_units = sorted((u for u in _UNITS if u != r's'), key=len, reverse=True)
    unit_pat = '|'.join(re.escape(u) for u in units)
    no_sep_unit_pat = '|'.join(re.escape(u) for u in no_sep_units)
    unit_boundary = r'(?![A-Za-z_])'
    spacing = (
        r'(?:[~ \t]+|'
        r'\\[,;:!][ \t]*|'
        r'\\(?:thinspace|medspace|thickspace|enspace|quad|qquad)[ \t]*|'
        r'\\hspace\*?\{[^}]+\}[ \t]*|'
        r'\\[ \t]+)'
    )

    # 1. Digit-ended numbers with an explicit, wrong-sized separator.
    explicit_digit_re = re.compile(
        r'(?P<num>(?<![A-Za-z\\])\d+(?:\.\d+)?)'
        r'(?P<sep>' + spacing + r')'
        r'(?P<unit>(?:' + unit_pat + r'))' + unit_boundary
    )
    text = explicit_digit_re.sub(r'\g<num>\\,\g<unit>', text)

    # 2. Digit-ended numbers with no separator, e.g. "100kN".
    no_sep_digit_re = re.compile(
        r'(?P<num>(?<![A-Za-z\\])\d+(?:\.\d+)?)'
        r'(?P<unit>(?:' + no_sep_unit_pat + r'))' + unit_boundary
    )
    text = no_sep_digit_re.sub(r'\g<num>\\,\g<unit>', text)

    # 3. Closing-dollar ended inline math, e.g. "$78$ kN" or "$EI = 78$~kN".
    # Require the content to end in a digit or closing brace/bracket so that
    # we don't touch e.g. "$x$ kN".
    dollar_expr = r'\$[^$\n]*[\d}\])]\$'
    explicit_dollar_re = re.compile(
        r'(?P<expr>' + dollar_expr + r')'
        r'(?P<sep>' + spacing + r')'
        r'(?P<unit>(?:' + unit_pat + r'))' + unit_boundary
    )
    text = explicit_dollar_re.sub(r'\g<expr>\\,\g<unit>', text)

    no_sep_dollar_re = re.compile(
        r'(?P<expr>' + dollar_expr + r')'
        r'(?P<unit>(?:' + no_sep_unit_pat + r'))' + unit_boundary
    )
    text = no_sep_dollar_re.sub(r'\g<expr>\\,\g<unit>', text)
    return text


def rule11_old_font_commands(text):
    """{\\bf text} -> \\textbf{text}, etc."""
    for old, new in _FONT_MAP.items():
        pattern = re.compile(r'\{\\' + old + r'\s+([^{}]+)\}')
        text = pattern.sub(r'\\' + new + r'{\1}', text)
    return text


def rule12_ellipsis(text):
    """... -> \\dots (not in comments or verbatim)."""
    lines = text.split('\n')
    result = []
    in_verbatim = False
    for line in lines:
        if re.match(r'^\s*\\begin\{(verbatim|lstlisting)\}', line):
            in_verbatim = True
        if re.match(r'^\s*\\end\{(verbatim|lstlisting)\}', line):
            in_verbatim = False
        if in_verbatim or line.strip().startswith('%'):
            result.append(line)
            continue
        result.append(re.sub(r'(?<!\\)\.\.\.', r'\\dots', line))
    return '\n'.join(result)


def rule13_ordinal_suffixes(text):
    """Convert superscript ordinal suffixes to plain text (1st, 2nd, ...)."""
    suffix = r'(st|nd|rd|th)'
    wrapped_suffix = (
        r'(?:\\(?:text|textrm|mathrm)\{\s*' + suffix + r'\s*\}|'
        + suffix + r')'
    )

    def suffix_text(match):
        # Each pattern has two possible suffix capture groups: one for wrapped
        # suffixes such as \text{st}, and one for bare suffixes such as {st}.
        return match.group(1) + (match.group(2) or match.group(3)).lower()

    whole_math_re = re.compile(
        r'\$\s*(\d+)\s*\^\s*(?:\{\s*)?' + wrapped_suffix +
        r'(?:\s*\})?\s*\$',
        re.IGNORECASE,
    )
    split_math_re = re.compile(
        r'(\d+)\s*\$\s*\^\s*(?:\{\s*)?' + wrapped_suffix +
        r'(?:\s*\})?\s*\$',
        re.IGNORECASE,
    )
    paren_math_re = re.compile(
        r'\\\(\s*(\d+)\s*\^\s*(?:\{\s*)?' + wrapped_suffix +
        r'(?:\s*\})?\s*\\\)',
        re.IGNORECASE,
    )
    textsup_re = re.compile(
        r'(\d+)\\textsuperscript\{\s*' + suffix + r'\s*\}',
        re.IGNORECASE,
    )

    lines = text.split('\n')
    result = []
    in_verbatim = False
    for line in lines:
        if re.match(r'^\s*\\begin\{(verbatim|lstlisting)\}', line):
            in_verbatim = True
        if re.match(r'^\s*\\end\{(verbatim|lstlisting)\}', line):
            in_verbatim = False
        if in_verbatim or line.strip().startswith('%'):
            result.append(line)
            continue

        line = whole_math_re.sub(suffix_text, line)
        line = split_math_re.sub(suffix_text, line)
        line = paren_math_re.sub(suffix_text, line)
        line = textsup_re.sub(lambda m: m.group(1) + m.group(2).lower(), line)
        result.append(line)
    return '\n'.join(result)


# ── Warnings ─────────────────────────────────────────────────────────

def warn_hardcoded_refs(text, filename):
    """Detect 'Figure 3', 'Table 2' etc. without \\ref."""
    warnings = []
    labels = (r'Figure', r'Figures', r'Fig\.', r'Figs\.',
              r'Table', r'Tables', r'Tab\.',
              r'Equation', r'Equations', r'Eq\.', r'Eqs\.',
              r'Section', r'Sections', r'Sec\.', r'Secs\.',
              r'Chapter', r'Chapters', r'Ch\.',
              r'Appendix', r'Appendices', r'App\.')
    pattern = re.compile(r'(?:' + '|'.join(labels) + r')\s+\d', re.MULTILINE)
    for i, line in enumerate(text.split('\n'), 1):
        if line.strip().startswith('%'):
            continue
        for m in pattern.finditer(line):
            before = line[:m.start()]
            if before.endswith(('\\cref{', '\\ref{', '\\Cref{')):
                continue
            warnings.append((filename, i, f'possible hardcoded ref: "{m.group()}"'))
    return warnings


def warn_manual_sizing(text, filename):
    """Detect \\big, \\Big, \\bigg, \\Bigg etc."""
    warnings = []
    pattern = re.compile(r'\\[bB]ig{1,2}[lrm]?\b')
    for i, line in enumerate(text.split('\n'), 1):
        if line.strip().startswith('%'):
            continue
        for m in pattern.finditer(line):
            warnings.append((filename, i, f'manual sizing: "{m.group()}"'))
    return warnings


LONG_FILE_THRESHOLD = 2000


def warn_long_file(text, filename):
    """Suggest \\input splitting for files over the threshold."""
    n_lines = len(text.split('\n'))
    if n_lines > LONG_FILE_THRESHOLD:
        return [(filename, 0,
                 f'file is {n_lines} lines — consider splitting with \\input')]
    return []


def warn_float_after_heading(text, filename):
    """Detect float environments placed directly after a heading."""
    warnings = []
    heading_re = re.compile(r'^\s*\\(?:sub)*section\*?\{')
    label_re = re.compile(r'^\s*\\label\{')
    float_re = re.compile(r'^\s*\\begin\{(figure|table|algorithm)\}')
    lines = text.split('\n')
    saw_heading = False
    heading_line = 0
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if heading_re.match(line):
            saw_heading = True
            heading_line = i
        elif saw_heading:
            if stripped == '' or stripped == '%' or label_re.match(line):
                continue
            m = float_re.match(line)
            if m:
                warnings.append((filename, i,
                    f'\\begin{{{m.group(1)}}} directly after heading '
                    f'(line {heading_line}) — move after introductory text'))
            saw_heading = False
    return warnings


# ── Rule registry ───────────────────────────────────────────────────
# Order matters for fixes: decorative comments must be stripped before
# sentence splitting, labels merged before heading spacing, etc.

RULES = [
    # Fixable rules (order determines application sequence)
    Rule( 1, 'labels_inline',        'Merge \\label onto the same line as \\section',              rule1_labels_inline,            weight=8, fixable=True,  order=10),
    Rule( 2, 'decorative_comments',  'Strip decorative comment separators (%%===, %%--- etc.)',    rule7_strip_decorative_comments, weight=6, fixable=True,  order=20),
    Rule( 3, 'heading_spacing',      'Two blank lines before headings, none after',                rule5_heading_spacing,           weight=7, fixable=True,  order=30),
    Rule( 4, 'equation_separators',  'Insert % lines around display-math environments',          rule2_equation_separators,       weight=7, fixable=True,  order=40),
    Rule( 5, 'equation_punctuation', 'Add trailing comma or period to display equations',         rule4_equation_punctuation,      weight=6, fixable=True,  order=50),
    Rule( 6, 'float_indentation',    'Tab-indent content inside figure/table/list environments',  rule6_figure_indentation,        weight=5, fixable=True,  order=60),
    Rule( 7, 'one_sentence_per_line','Split sentences onto individual lines',                     rule3_one_sentence_per_line,     weight=8, fixable=True,  order=70),
    Rule( 8, 'math_delimiters_inline','Replace \\(...\\) with $...$',                           rule8_math_delimiters_inline,   weight=5, fixable=True,  order=80),
    Rule( 9, 'tilde_before_refs',    'Ensure non-breaking space before \\ref, \\cite etc.',       rule9_tilde_before_refs,         weight=7, fixable=True,  order=90),
    Rule(10, 'number_unit_spacing',  'Normalise number-unit spacing (100\\,kN)',                 rule10_number_unit_spacing,      weight=6, fixable=True,  order=100),
    Rule(11, 'old_font_commands',    'Replace {\\bf text} with \\textbf{text} etc.',              rule11_old_font_commands,        weight=5, fixable=True,  order=110),
    Rule(12, 'ellipsis',             'Replace ... with \\dots',                                   rule12_ellipsis,                 weight=4, fixable=True,  order=120),
    Rule(13, 'ordinal_suffixes',     'Convert superscript ordinals to plain text (1st, 2nd)',     rule13_ordinal_suffixes,         weight=8, fixable=True,  order=130),
    # Unfixable rules (warnings / clunks)
    Rule(14, 'long_file',            'Warn if file exceeds 2000 lines',                           warn_long_file,                  weight=3, fixable=False, order=200),
    Rule(15, 'hardcoded_refs',       'Detect "Figure 3" instead of \\cref{...}',                  warn_hardcoded_refs,             weight=6, fixable=False, order=210),
    Rule(16, 'manual_sizing',        'Detect \\big, \\Big etc. (prefer \\left/\\right)',          warn_manual_sizing,              weight=3, fixable=False, order=220),
    Rule(17, 'float_after_heading',  'Detect float placed directly after a heading',              warn_float_after_heading,        weight=4, fixable=False, order=230),
    # New rules are appended so existing numeric configuration remains stable.
    Rule(18, 'math_delimiters_display','Replace \\[...\\] with $$...$$',                         rule18_math_delimiters_display, weight=0, fixable=True,  order=85),
    Rule(19, 'math_delimiters_equation','Replace \\[...\\] or $$...$$ with equation environment', rule19_math_delimiters_equation, weight=0, fixable=True,  order=35),
]


def _get_rule(rule_id):
    """Look up a rule by id."""
    for r in RULES:
        if r.id == rule_id:
            return r
    return None


def _get_rule_by_num(num):
    """Look up a rule by its number."""
    for r in RULES:
        if r.num == num:
            return r
    return None


# ── Config ──────────────────────────────────────────────────────────

def load_config(path=None):
    """Load config from .clat.toml or fallback locations.

    Returns a dict with 'threshold' (int) and 'weights' (dict[str, int]).
    """
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib
    from pathlib import Path

    search_paths = []
    if path:
        search_paths.append(Path(path))
    else:
        search_paths.append(Path.cwd() / '.clat.toml')
        config_home = Path.home() / '.config' / 'clat' / 'config.toml'
        search_paths.append(config_home)

    for p in search_paths:
        if p.is_file():
            with open(p, 'rb') as f:
                data = tomllib.load(f)
            return {
                'threshold': data.get('threshold', DEFAULT_THRESHOLD),
                'weights': data.get('weights', {}),
            }

    return {'threshold': DEFAULT_THRESHOLD, 'weights': {}}


_LEGACY_WEIGHT_IDS = {
    'math_delimiters_inline': 'math_delimiters',
    'math_delimiters_display': 'math_delimiters',
}


def _effective_weight(rule, config):
    """Return the weight for a rule, with config override if present."""
    weights = config['weights']
    if rule.id in weights:
        return weights[rule.id]
    legacy_id = _LEGACY_WEIGHT_IDS.get(rule.id)
    if legacy_id and legacy_id in weights:
        return weights[legacy_id]
    return rule.weight


def generate_default_config():
    """Return a .clat.toml string with all rules and their default weights."""
    lines = [
        '# clat configuration',
        '# Adjust threshold and per-rule weights to taste.',
        '#',
        '# Categories are determined at runtime:',
        '#   clang:  weight >= threshold AND fixable     (auto-fixed)',
        '#   clunk:  weight >= threshold AND NOT fixable  (needs your attention)',
        '#   splat:  0 < weight < threshold               (advisory)',
        '#   off:    weight <= 0                          (disabled)',
        '',
        f'threshold = {DEFAULT_THRESHOLD}',
        '',
        '[weights]',
    ]
    max_id = max(len(r.id) for r in RULES)
    for r in sorted(RULES, key=lambda r: r.num):
        tag = 'fixable' if r.fixable else 'unfixable'
        lines.append(f'{r.id:<{max_id}} = {r.weight:>2}  # {r.name} ({tag})')
    return '\n'.join(lines) + '\n'


def save_config(config, path):
    """Write config dict back to a .clat.toml file."""
    from pathlib import Path
    # Rebuild from current state, respecting any weight overrides
    lines = [
        '# clat configuration',
        '# Adjust threshold and per-rule weights to taste.',
        '#',
        '# Categories are determined at runtime:',
        '#   clang:  weight >= threshold AND fixable     (auto-fixed)',
        '#   clunk:  weight >= threshold AND NOT fixable  (needs your attention)',
        '#   splat:  0 < weight < threshold               (advisory)',
        '#   off:    weight <= 0                          (disabled)',
        '',
        f'threshold = {config["threshold"]}',
        '',
        '[weights]',
    ]
    max_id = max(len(r.id) for r in RULES)
    for r in sorted(RULES, key=lambda r: r.num):
        w = _effective_weight(r, config)
        tag = 'fixable' if r.fixable else 'unfixable'
        lines.append(f'{r.id:<{max_id}} = {w:>2}  # {r.name} ({tag})')
    Path(path).write_text('\n'.join(lines) + '\n')
    return path


# ── Main entry point ─────────────────────────────────────────────────

@dataclass
class ClatResult:
    """Result of running clat on a file.

    Attributes
    ----------
    text : str          — the (possibly modified) source text
    clangs : list[tuple] — (rule, count) for auto-fixed rules above threshold
    clunks : list[tuple] — (rule, filename, line, msg) for unfixable issues above threshold
    splats : list[tuple] — (rule, filename, line, msg) for issues below threshold
    """
    text: str
    clangs: list = field(default_factory=list)
    clunks: list = field(default_factory=list)
    splats: list = field(default_factory=list)


def texfmt(text, filename='<input>', config=None):
    """Apply formatting rules according to config.

    Returns a ClatResult with the formatted text and categorised issues.

    For backwards compatibility, also accessible as (text, warnings) via
    the legacy property — but prefer ClatResult directly.
    """
    if config is None:
        config = {'threshold': DEFAULT_THRESHOLD, 'weights': {}}

    threshold = config['threshold']
    result = ClatResult(text=text)

    # Sort rules by order for deterministic application
    sorted_rules = sorted(RULES, key=lambda r: r.order)

    for rule in sorted_rules:
        w = _effective_weight(rule, config)
        if w <= 0:
            continue

        if rule.fixable:
            original = result.text
            result.text = rule.fn(result.text)
            if result.text != original:
                orig_lines = original.split('\n')
                new_lines = result.text.split('\n')
                n_hits = (sum(1 for a, b in zip(orig_lines, new_lines)
                              if a != b)
                          + abs(len(orig_lines) - len(new_lines)))
                if w >= threshold:
                    result.clangs.append((rule, n_hits))
                else:
                    # Below threshold: still fix, but report as splat
                    result.splats.append((rule, filename, 0,
                                         f'{rule.name} (auto-fixed)'))
        else:
            issues = rule.fn(result.text, filename)
            for fname, line, msg in issues:
                if w >= threshold:
                    result.clunks.append((rule, fname, line, msg))
                else:
                    result.splats.append((rule, fname, line, msg))

    return result
