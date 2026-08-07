"""
clat formatting rules.

Every rule has a number, a default weight (1–10; 0 disables), and a fixable flag.
At runtime, the user's threshold decides what happens:

  clang:  weight >= threshold AND fixable      → auto-fixed
  clunk:  weight >= threshold AND NOT fixable   → must fix manually
  splat:  0 < weight < threshold                → advisory
  off:    weight <= 0                           → disabled

Fixable rules are swept to a text fixed point by default. Run ``clat list`` to
see all rules. Configure via ``.clat.toml`` or ``clat set <rule-id> <weight>``.
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

# ── Abbreviations that take an interword space ───────────────────────
# After abbreviations such as "e.g." or "et al." the trailing period reads to
# TeX as a full stop, so it inserts a wider end-of-sentence space.  Forcing a
# control space ("\ ") keeps it an ordinary interword space (which still
# stretches a little).
#
# ALWAYS abbreviations never end a sentence, so the space is fixed whatever
# follows.  MAYBE abbreviations can legitimately end a sentence, so they are
# only fixed before a clear continuation — a lowercase letter, digit, or an
# opening parenthesis — leaving a following capital alone as a possible full
# stop.
INTERWORD_ABBREVIATIONS_ALWAYS = (r'e\.g\.', r'i\.e\.', r'cf\.', r'viz\.', r'vs\.')
INTERWORD_ABBREVIATIONS_MAYBE = (r'et\s+al\.', r'etc\.')

_ABBR_ALWAYS_RE = re.compile(
    r'(?<![A-Za-z])(' + '|'.join(INTERWORD_ABBREVIATIONS_ALWAYS) + r')[ \t]+(?=\S)')
_ABBR_MAYBE_RE = re.compile(
    r'(?<![A-Za-z])(' + '|'.join(INTERWORD_ABBREVIATIONS_MAYBE) + r')[ \t]+(?=[a-z0-9(])')

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
DEFAULT_MAX_ITER = 5

# Environments whose contents are masked out before any rule runs, so prose
# rules don't mangle picture/plot syntax (coordinates, node text, lengths …).
# Configurable per project via ``protected_environments`` in .clat.toml.
DEFAULT_PROTECTED_ENVIRONMENTS = ('tikzpicture', 'pgfpicture', 'axis', 'tikzcd')


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


# ── Shared prose helpers (used by the sentence split/join rules) ─────
# rule3 (one_sentence_per_line) and rule18 (join_wrapped_lines) are inverse
# operations, so they must agree exactly on which lines are prose and where a
# sentence ends.  The shared regexes and helpers below keep the two in step.

_PROSE_SKIP_RE = re.compile(
    r'^\s*(%|\\begin|\\end|\\item|\\paragraph|\\section|\\subsection|'
    r'\\subsubsection|\\caption|\\label|\\centering|\\includegraphics|'
    r'\\toprule|\\midrule|\\bottomrule|\\hline|\\RequirePackage|'
    r'\\usepackage|\\newcommand|\\renewcommand|\\def|\\let|\\input|'
    r'\\bibliography|\\documentclass|\\title|\\author|\\address|'
    r'\\ead|\\cortext|\\journal|\\bibliographystyle|\\addtolength|'
    r'\\(?:addvspace|hspace|vspace|setlength|rule|resizebox|raisebox|'
    r'vskip|hskip|kern|mkern|raise|lower)\b|'
    r'\\Require|\\Ensure|\\Statex|\\State|\\For|\\EndFor|\\If|\\EndIf)'
)

# Environments whose bodies are never split or joined as prose.
_PROSE_ENV_BEGIN_RE = re.compile(
    r'^\s*\\begin\{(equation|align|table|tabular|figure|algorithm|'
    r'algorithmic|keyword|frontmatter|verbatim|lstlisting)\*?\}')
_PROSE_ENV_END_RE = re.compile(
    r'^\s*\\end\{(equation|align|table|tabular|figure|algorithm|'
    r'algorithmic|keyword|frontmatter|verbatim|lstlisting)\*?\}')

_ITEM_RE = re.compile(r'^\s*\\item\b')

# Prefix of the sentinel _mask_environments leaves in place of a masked picture
# block; the join rule must treat it as a boundary, never merging across it.
_PROTECT_SENTINEL_PREFIX = '\x01CLAT-PROTECTED-'

# Trailing math/quote/bracket closers to strip before looking for a sentence
# terminator, so a sentence ending inside "$$...$$", "\emph{...}", or quotes
# still reads as terminated (e.g. "...$$E = mc^2.$$" ends a sentence).
_SENTENCE_CLOSERS_RE = re.compile(
    r'(?:\$+|\\[)\]]|[)\]}\'"`»”’])+\s*$'
)


def _ends_sentence(line):
    """True if ``line`` ends a sentence (terminal .?! after closers/abbrevs)."""
    protected = PROTECT_RE.sub(lambda m: m.group(0)[:-1] + PLACEHOLDER, line)
    stripped = _SENTENCE_CLOSERS_RE.sub('', protected.rstrip()).rstrip()
    return bool(stripped) and stripped[-1] in '.?!'


def _has_inline_comment(line):
    """True if ``line`` carries an unescaped ``%`` comment."""
    return re.search(r'(?<!\\)%', line) is not None


def _brace_balance(line):
    """Net count of unescaped ``{`` minus ``}`` (comment tail ignored)."""
    line = re.sub(r'(?<!\\)%.*$', '', line)
    opens = len(re.findall(r'(?<!\\)\{', line))
    closes = len(re.findall(r'(?<!\\)\}', line))
    return opens - closes


# Captions are prose embedded in otherwise non-prose float environments.  Keep
# their command line structural, but reflow their mandatory argument with the
# same complementary join/split rules as ordinary prose.
_CAPTION_START_RE = re.compile(
    r'(?m)^(?P<indent>[ \t]*)[^%\n]*?\\caption\*?(?![A-Za-z@])'
    r'(?:[ \t]*\[[^\]\n]*\])?[ \t]*(?:\n[ \t]*)?\{')
_CAPTION_NON_PROSE_ENV_RE = re.compile(
    r'\\(?P<action>begin|end)\{(?P<env>equation|align|tabular|algorithmic|'
    r'keyword|frontmatter|verbatim|lstlisting)\*?\}')


def _caption_is_in_non_prose_environment(text, position):
    """Whether ``position`` is inside a protected, non-float environment."""
    environments = []
    for line in text[:position].split('\n'):
        # An environment command in a TeX comment does not change the context.
        line = re.sub(r'(?<!\\)%.*$', '', line)
        for match in _CAPTION_NON_PROSE_ENV_RE.finditer(line):
            env = match.group('env')
            if match.group('action') == 'begin':
                environments.append(env)
            elif env in environments:
                environments.pop(len(environments) - 1
                                 - environments[::-1].index(env))
    return bool(environments)


def _matching_brace(text, opening):
    """Return the closing brace matching ``opening``, or ``None`` if absent."""
    depth = 0
    in_comment = False
    i = opening
    while i < len(text):
        char = text[i]
        if char == '\n':
            in_comment = False
        elif in_comment:
            i += 1
            continue
        elif char == '\\':
            # Skip the escaped character, including escaped braces and percent
            # signs.  Two backslashes leave a following brace unescaped.
            i += 2
            continue
        elif char == '%':
            in_comment = True
        elif char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return None


def _format_caption_bodies(text, formatter):
    """Apply ``formatter(body, indent)`` to every complete ``\\caption`` body."""
    result = []
    pos = 0
    for match in _CAPTION_START_RE.finditer(text):
        # A nested-looking caption command belongs to an already handled body.
        # Do not alter literal caption text in verbatim-like environments.
        if (match.start() < pos
                or _caption_is_in_non_prose_environment(text, match.start())):
            continue
        opening = match.end() - 1
        closing = _matching_brace(text, opening)
        if closing is None:
            continue
        result.append(text[pos:opening + 1])
        result.append(formatter(text[opening + 1:closing], match.group('indent')))
        pos = closing
    result.append(text[pos:])
    return ''.join(result)


# A new sentence can begin with a capital letter or a LaTeX control word such
# as ``\AS{...}``; both must be valid split points after its terminator.
_SENTENCE_SPLIT_RE = re.compile(
    r'(?P<ending>[.?!]+(?:\$+|\\\]|[)\]}\'"`»”’])*)'
    r'(?P<space>[ \t]+)(?=[A-Z]|\\[A-Za-z@])')


def _split_sentences(line):
    """Return the non-empty sentence-sized pieces of one prose line."""
    protected = PROTECT_RE.sub(lambda m: m.group(0)[:-1] + PLACEHOLDER, line)
    sentences = []
    start = 0
    for match in _SENTENCE_SPLIT_RE.finditer(protected):
        # Keep the terminator and any trailing math/quote/bracket closers with
        # the preceding sentence, and discard only its following whitespace.
        sentences.append(protected[start:match.start('space')])
        start = match.end('space')
    sentences.append(protected[start:])
    return [s.replace(PLACEHOLDER, '.') for s in sentences if s.strip()]


def _split_caption_sentences(body, indent):
    """Split caption prose and indent continuation sentences like its command."""
    result = []
    for line_number, line in enumerate(body.split('\n')):
        leading = re.match(r'^[ \t]*', line).group(0)
        sentences = _split_sentences(line[len(leading):])
        if not sentences:
            result.append(line)
            continue
        # A physical continuation line should be indented with the caption even
        # if it arrived unindented; retain any deeper indentation it already has.
        first_indent = leading if line_number == 0 or leading else indent
        for sentence_number, sentence in enumerate(sentences):
            result.append((first_indent if sentence_number == 0 else indent)
                          + sentence)
    return '\n'.join(result)


def _join_caption_lines(body, indent):
    """Join hard-wrapped caption lines without crossing sentence boundaries."""
    result = []
    buffer = None

    def flush():
        nonlocal buffer
        if buffer is not None:
            result.append(buffer)
            buffer = None

    for line in body.split('\n'):
        stripped = line.strip()
        if not stripped:
            flush()
            result.append('')
        elif buffer is None:
            buffer = stripped
        elif _ends_sentence(buffer) or _has_inline_comment(buffer):
            flush()
            buffer = stripped
        else:
            buffer = buffer.rstrip() + ' ' + stripped
    flush()
    return ('\n' + indent).join(result)


def rule3_one_sentence_per_line(text):
    """Split sentences onto individual lines, protecting abbreviations."""
    text = _format_caption_bodies(text, _split_caption_sentences)
    lines = text.split('\n')
    result = []
    in_env = 0
    for line in lines:
        stripped = line.strip()
        if _PROSE_ENV_BEGIN_RE.match(line):
            in_env += 1
        if _PROSE_ENV_END_RE.match(line):
            in_env = max(0, in_env - 1)
            result.append(line)
            continue
        if in_env or not stripped or stripped == '%' or _PROSE_SKIP_RE.match(stripped):
            result.append(line)
            continue
        result.extend(_split_sentences(line))
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


def rule9_math_delimiters_display(text):
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


def rule10_math_delimiters_equation(text):
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


def rule11_tilde_before_refs(text):
    """Ensure ~ before \\ref, \\cref, \\eqref, \\cite."""
    return re.sub(
        r'(?<=[A-Za-z0-9).])\s+(\\(?:c?ref|eqref|cite|Cref)\{)',
        r'~\1', text)


_DIMENSION_ARGUMENT_COMMANDS = {
    'addtolength': (1,),
    'addvspace': (0,),
    'hspace': (0,),
    'parbox': (0,),
    'raisebox': (0,),
    'resizebox': (0, 1),
    'rule': (0, 1),
    'setlength': (1,),
    'vspace': (0,),
}
_DIMENSION_COMMAND_RE = re.compile(
    r'\\(?P<command>'
    + '|'.join(sorted(_DIMENSION_ARGUMENT_COMMANDS, key=len, reverse=True))
    + r')\*?(?![A-Za-z@])'
)
_DIMENSION_ENV_BEGIN_RE = re.compile(
    r'\\begin\s*\{\s*(?:minipage|varwidth)\*?\s*\}'
)
_DIMENSION_PRIMITIVE_RE = re.compile(
    r'\\(?:hskip|kern|lower|mkern|raise|vskip)(?![A-Za-z@])'
)


def _matching_bracket(text, opening):
    """Return the closing bracket matching ``opening``, or ``None`` if absent."""
    depth = 0
    i = opening
    while i < len(text):
        char = text[i]
        if char == '\\':
            i += 2
            continue
        if char == '[':
            depth += 1
        elif char == ']':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return None


def _skip_optional_arguments(text, position):
    """Advance past whitespace and any complete optional ``[...]`` arguments."""
    while True:
        while position < len(text) and text[position].isspace():
            position += 1
        if position >= len(text) or text[position] != '[':
            return position
        closing = _matching_bracket(text, position)
        if closing is None:
            return len(text)
        position = closing + 1


def _dimension_argument_spans(text, primitive_dimension_re):
    """Return spans of known TeX dimension arguments within ``text``.

    The number--unit rule is intentionally active in text macros, so simply
    ignoring every braced argument would lose valid prose fixes.  Instead,
    recognise the mandatory arguments of core length commands and leave only
    those spans untouched.
    """
    spans = []

    for match in _DIMENSION_COMMAND_RE.finditer(text):
        wanted = _DIMENSION_ARGUMENT_COMMANDS[match.group('command')]
        position = match.end()
        for index in range(max(wanted) + 1):
            position = _skip_optional_arguments(text, position)
            if position >= len(text) or text[position] != '{':
                break
            closing = _matching_brace(text, position)
            if closing is None:
                break
            if index in wanted:
                spans.append((position, closing + 1))
            position = closing + 1

    # These environments take their width as the first mandatory argument
    # after \begin{...}, with any optional arguments first.
    for match in _DIMENSION_ENV_BEGIN_RE.finditer(text):
        position = _skip_optional_arguments(text, match.end())
        if position < len(text) and text[position] == '{':
            closing = _matching_brace(text, position)
            if closing is not None:
                spans.append((position, closing + 1))

    # TeX primitives accept an unbraced length.  Protect the length and any
    # ``plus``/``minus`` components, while leaving following prose available to
    # the rule.
    for match in _DIMENSION_PRIMITIVE_RE.finditer(text):
        position = match.end()
        while position < len(text) and text[position].isspace():
            position += 1
        dimension = primitive_dimension_re.match(text, position)
        if dimension:
            spans.append((dimension.start(), dimension.end()))

    return sorted(spans)


def rule12_number_unit_spacing(text):
    """Normalise number-unit spacing to a non-expanding thin space.

    Handles ordinary spaces, non-breaking spaces, LaTeX spacing commands, and
    missing spaces:
      * ``100 kN``, ``100~kN`` or ``100kN``       -> ``100\\,kN``
      * ``100\\;kN`` or ``100\\quad kN``          -> ``100\\,kN``
      * ``$78$ kN``, ``$78$~kN`` or ``$78$kN``    -> ``$78$\\,kN``
      * ``$EI = 200$ MN`` or ``$EI = 200$MN``     -> ``$EI = 200$\\,MN``

    Already-correct ``\\,`` spacing is left unchanged.  No-space fixes exclude
    bare ``s`` to avoid turning decades such as ``1990s`` into units.

    Only the document body is touched.  In the preamble, after a ``=`` or
    ``[``, and in core LaTeX length-command arguments (for example,
    ``\\vspace{1cm}``), a number and unit form a TeX dimension rather than
    prose, so they are left alone.
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

    # A number that opens a key=value option or a bracket argument
    # (margin=25mm, width=100mm, \\[10mm]) is a TeX dimension, not prose, and
    # must not gain a \,: exclude a preceding '=' or '[' as well as letters.
    # A preceding digit is excluded too so a match cannot start mid-number
    # (which would otherwise sneak a \, into the tail of a guarded number).
    num_start = r'(?<![A-Za-z\\=\[\d])'

    # 1. Digit-ended numbers with an explicit, wrong-sized separator.
    explicit_digit_re = re.compile(
        r'(?P<num>' + num_start + r'\d+(?:\.\d+)?)'
        r'(?P<sep>' + spacing + r')'
        r'(?P<unit>(?:' + unit_pat + r'))' + unit_boundary
    )

    # 2. Digit-ended numbers with no separator, e.g. "100kN".
    no_sep_digit_re = re.compile(
        r'(?P<num>' + num_start + r'\d+(?:\.\d+)?)'
        r'(?P<unit>(?:' + no_sep_unit_pat + r'))' + unit_boundary
    )

    # 3. Closing-dollar ended inline math, e.g. "$78$ kN" or "$EI = 78$~kN".
    # Require the content to end in a digit or closing brace/bracket so that
    # we don't touch e.g. "$x$ kN".
    dollar_expr = r'\$[^$\n]*[\d}\])]\$'
    explicit_dollar_re = re.compile(
        r'(?P<expr>' + dollar_expr + r')'
        r'(?P<sep>' + spacing + r')'
        r'(?P<unit>(?:' + unit_pat + r'))' + unit_boundary
    )
    no_sep_dollar_re = re.compile(
        r'(?P<expr>' + dollar_expr + r')'
        r'(?P<unit>(?:' + no_sep_unit_pat + r'))' + unit_boundary
    )

    def _space_units(chunk):
        chunk = explicit_digit_re.sub(r'\g<num>\\,\g<unit>', chunk)
        chunk = no_sep_digit_re.sub(r'\g<num>\\,\g<unit>', chunk)
        chunk = explicit_dollar_re.sub(r'\g<expr>\\,\g<unit>', chunk)
        chunk = no_sep_dollar_re.sub(r'\g<expr>\\,\g<unit>', chunk)
        return chunk

    primitive_dimension_re = re.compile(
        r'[+-]?\d+(?:\.\d+)?[ \t]*(?:' + unit_pat + r')' + unit_boundary
        + r'(?:\s+(?:plus|minus)\s+[+-]?\d+(?:\.\d+)?[ \t]*(?:'
        + unit_pat + r')' + unit_boundary + r')*'
    )

    def _space_prose(chunk):
        result = []
        position = 0
        for start, end in _dimension_argument_spans(chunk, primitive_dimension_re):
            # A command nested in an already protected argument needs no
            # separate handling; retaining the larger span preserves it all.
            if start < position:
                continue
            result.append(_space_units(chunk[position:start]))
            result.append(chunk[start:end])
            position = end
        result.append(_space_units(chunk[position:]))
        return ''.join(result)

    # Unit spacing is a text-mode prose fix.  The preamble is all commands and
    # package options (e.g. geometry lengths) where \, is invalid, so restrict
    # the fix to the document body.  A fragment with no \begin{document} (an
    # \input-ed chapter, say) is treated as body.
    begin = re.search(r'\\begin\{document\}', text)
    if not begin:
        return _space_prose(text)
    end = re.search(r'\\end\{document\}', text)
    body_end = end.start() if end else len(text)
    return (text[:begin.end()]
            + _space_prose(text[begin.end():body_end])
            + text[body_end:])


def rule13_old_font_commands(text):
    """{\\bf text} -> \\textbf{text}, etc."""
    for old, new in _FONT_MAP.items():
        pattern = re.compile(r'\{\\' + old + r'\s+([^{}]+)\}')
        text = pattern.sub(r'\\' + new + r'{\1}', text)
    return text


def rule14_ellipsis(text):
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


def rule15_ordinal_suffixes(text):
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


def rule16_table_line_endings(text):
    r"""Move \\\\ and \hline/\toprule/etc. to proper positions in tables.

    Ensures:
      1. Line endings (\\\\) are on the same line as the table row content.
      2. Horizontal rules (\hline, \toprule, \midrule, \bottomrule) are on their
         own lines, not on the same line as row content.
    """
    lines = text.split('\n')
    result = []
    in_tabular = False

    table_envs = re.compile(r'^\s*\\begin\{(tabular|table|array)\b')
    end_table_envs = re.compile(r'^\s*\\end\{(tabular|table|array)\b')
    hline_cmd_re = re.compile(r'\\(?:hline|toprule|midrule|bottomrule)\b')
    hline_only_re = re.compile(r'^\s*(\\(?:hline|toprule|midrule|bottomrule))\s*(?:\\\\)?\s*$')
    backslash_only_re = re.compile(r'^\s*\\\\\s*$')

    def split_hline_segments(line):
        """Split horizontal rules away from row content on the same line."""
        if not hline_cmd_re.search(line):
            return [line]
        indent = re.match(r'^\s*', line).group(0)
        segments = []
        cursor = 0
        for match in hline_cmd_re.finditer(line):
            before = line[cursor:match.start()].strip()
            if before:
                segments.append(indent + before)
            segments.append(indent + match.group(0))
            cursor = match.end()
        after = line[cursor:].strip()
        if after:
            segments.append(indent + after)
        return segments

    for line in lines:
        if table_envs.match(line):
            in_tabular = True
        if end_table_envs.match(line):
            in_tabular = False

        if not in_tabular:
            result.append(line)
            continue

        for segment in split_hline_segments(line):
            match = hline_only_re.match(segment)
            if match:
                indent = re.match(r'^\s*', segment).group(0)
                result.append(indent + match.group(1))
                continue

            if backslash_only_re.match(segment) and result:
                prev = result[-1]
                if hline_only_re.match(prev):
                    continue
                if not prev.rstrip().endswith('\\\\'):
                    result[-1] = prev.rstrip() + ' \\\\'
                    continue

            result.append(segment)

    return '\n'.join(result)


def rule17_abbreviation_spacing(text):
    r"""Force an ordinary interword space after abbreviations like ``e.g.``.

    The trailing period of ``e.g.``, ``i.e.``, ``et al.`` and friends otherwise
    reads to TeX as a full stop, producing a wider end-of-sentence space.
    Replacing the following space with a control space (``\ ``) keeps it an
    ordinary interword space (which still stretches a little).

    ``e.g.``, ``i.e.``, ``cf.``, ``viz.`` and ``vs.`` never end a sentence and
    are always fixed.  ``et al.`` and ``etc.`` can end a sentence, so they are
    only fixed before a clear continuation (a lowercase letter, digit, or an
    opening parenthesis); a following capital is left untouched.  Comments and
    verbatim blocks are skipped.
    """
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
        line = _ABBR_ALWAYS_RE.sub(r'\1\\ ', line)
        line = _ABBR_MAYBE_RE.sub(r'\1\\ ', line)
        result.append(line)
    return '\n'.join(result)


def rule18_join_wrapped_lines(text):
    r"""Join hard-wrapped prose lines so each sentence is on one line.

    The inverse of :func:`rule3_one_sentence_per_line`: where that rule *splits*
    a line carrying several sentences, this one *joins* a sentence that has been
    hard-wrapped across several lines.  Running both settles prose to exactly one
    sentence per line rather than leaving mid-sentence line breaks behind.

    A prose line is joined onto the current run unless the run already ends a
    sentence — a terminal ``.``/``?``/``!`` (after abbreviation protection and
    any trailing math/quote/bracket closers).  That test is the exact inverse of
    rule3's split point, so the two rules reach a fixed point instead of fighting
    across sweeps.

    Boundaries that never join across: blank lines, comments, protected
    environments (equation, table, figure, verbatim, ...), masked
    picture sentinels, and structural commands.  An ``\item`` starts a fresh run
    so its wrapped body is gathered without being pulled onto the line above; a
    structural command left with open braces — a heading title wrapped across
    lines — absorbs continuation lines until the braces balance, so the title
    becomes one line and never leaks into the following prose.  Caption bodies
    are the exception to float protection: they are prose and are reflowed.
    """
    text = _format_caption_bodies(text, _join_caption_lines)
    lines = text.split('\n')
    result = []
    buffer = None  # text of the run being accumulated, or None

    def flush():
        nonlocal buffer
        if buffer is not None:
            result.append(buffer)
            buffer = None

    in_env = 0
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Protected environments (same set as rule3): bodies are left verbatim.
        if _PROSE_ENV_BEGIN_RE.match(line):
            in_env += 1
        if _PROSE_ENV_END_RE.match(line):
            in_env = max(0, in_env - 1)
            flush()
            result.append(line)
            i += 1
            continue
        if in_env:
            flush()
            result.append(line)
            i += 1
            continue

        # Hard boundaries: blank lines, comments, masked picture sentinels.
        if (not stripped or stripped.startswith('%')
                or _PROTECT_SENTINEL_PREFIX in line):
            flush()
            result.append(line)
            i += 1
            continue

        # \item begins a fresh joinable run: its wrapped body is gathered, but it
        # is never appended onto the preceding line.
        if _ITEM_RE.match(line):
            flush()
            buffer = line.rstrip()
            i += 1
            continue

        # Other structural commands are boundaries.  If such a line leaves its
        # braces open (a heading title wrapped across lines), absorb continuation
        # lines until the braces balance so the title stays a single line.
        if _PROSE_SKIP_RE.match(stripped):
            flush()
            merged = line.rstrip()
            while (_brace_balance(merged) > 0 and i + 1 < n
                   and lines[i + 1].strip()
                   and not lines[i + 1].strip().startswith('%')):
                i += 1
                merged = merged.rstrip() + ' ' + lines[i].strip()
            result.append(merged)
            i += 1
            continue

        # Prose: join onto the current run unless it already ends a sentence (or
        # carries an inline comment that would swallow the appended text).
        if buffer is None:
            buffer = line.rstrip()
        elif _ends_sentence(buffer) or _has_inline_comment(buffer):
            flush()
            buffer = line.rstrip()
        else:
            buffer = buffer.rstrip() + ' ' + stripped
        i += 1

    flush()
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
    Rule( 8, 'math_delimiters_inline','Replace \\(...\\) with $...$',                           rule8_math_delimiters_inline,    weight=5, fixable=True,  order=80),
    Rule( 9, 'math_delimiters_display','Replace \\[...\\] with $$...$$',                         rule9_math_delimiters_display,   weight=0, fixable=True,  order=85),
    Rule(10, 'math_delimiters_equation','Replace \\[...\\] or $$...$$ with equation environment', rule10_math_delimiters_equation, weight=0, fixable=True,  order=35),
    Rule(11, 'tilde_before_refs',    'Ensure non-breaking space before \\ref, \\cite etc.',       rule11_tilde_before_refs,        weight=7, fixable=True,  order=90),
    Rule(12, 'number_unit_spacing',  'Normalise number-unit spacing (100\\,kN)',                 rule12_number_unit_spacing,      weight=6, fixable=True,  order=100),
    Rule(13, 'old_font_commands',    'Replace {\\bf text} with \\textbf{text} etc.',              rule13_old_font_commands,        weight=5, fixable=True,  order=110),
    Rule(14, 'ellipsis',             'Replace ... with \\dots',                                   rule14_ellipsis,                 weight=4, fixable=True,  order=120),
    Rule(15, 'ordinal_suffixes',     'Convert superscript ordinals to plain text (1st, 2nd)',     rule15_ordinal_suffixes,         weight=8, fixable=True,  order=130),
    Rule(16, 'table_line_endings',    'Table \\\\ on row line, \\hline/\\toprule on own line',      rule16_table_line_endings,       weight=7, fixable=True,  order=140),
    Rule(17, 'abbreviation_spacing',  'Force interword space after e.g., i.e., et al.',            rule17_abbreviation_spacing,     weight=7, fixable=True,  order=145),
    Rule(22, 'join_wrapped_lines',    'Join hard-wrapped lines so each sentence is one line',      rule18_join_wrapped_lines,       weight=8, fixable=True,  order=65),
    # Unfixable rules (warnings / clunks)
    Rule(18, 'long_file',            'Warn if file exceeds 2000 lines',                           warn_long_file,                  weight=3, fixable=False, order=200),
    Rule(19, 'hardcoded_refs',       'Detect "Figure 3" instead of \\cref{...}',                  warn_hardcoded_refs,             weight=6, fixable=False, order=210),
    Rule(20, 'manual_sizing',        'Detect \\big, \\Big etc. (prefer \\left/\\right)',          warn_manual_sizing,              weight=3, fixable=False, order=220),
    Rule(21, 'float_after_heading',  'Detect float placed directly after a heading',              warn_float_after_heading,        weight=4, fixable=False, order=230),
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

def _default_config():
    """A config dict with all defaults and no user overrides."""
    return {
        'threshold': DEFAULT_THRESHOLD,
        'weights': {},
        'protected_environments': list(DEFAULT_PROTECTED_ENVIRONMENTS),
        'unprotected_rules': [],
    }


def load_config(path=None):
    """Load config from .clat.toml or fallback locations.

    Returns a dict with 'threshold' (int), 'weights' (dict[str, int]),
    'protected_environments' (list[str]), and 'unprotected_rules' (list[str]).
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
                'protected_environments': data.get(
                    'protected_environments',
                    list(DEFAULT_PROTECTED_ENVIRONMENTS)),
                'unprotected_rules': data.get('unprotected_rules', []),
            }

    return _default_config()


def _effective_weight(rule, config):
    """Return the weight for a rule, with config override if present."""
    return config['weights'].get(rule.id, rule.weight)


def _toml_str_list(items):
    """Render a list of strings as a TOML inline array."""
    return '[' + ', '.join(f'"{item}"' for item in items) + ']'


def _config_lines(threshold, envs, unprotected):
    """Header, threshold, and environment-protection lines for a config file."""
    return [
        '# clat configuration',
        '# Adjust threshold and per-rule weights to taste.',
        '#',
        '# Categories are determined at runtime:',
        '#   clang:  weight >= threshold AND fixable     (auto-fixed)',
        '#   clunk:  weight >= threshold AND NOT fixable  (needs your attention)',
        '#   splat:  0 < weight < threshold               (advisory)',
        '#   off:    weight <= 0                          (disabled)',
        '',
        f'threshold = {threshold}',
        '',
        '# Contents of these environments are left untouched by every rule.',
        f'protected_environments = {_toml_str_list(envs)}',
        '# Rule ids listed here still run inside protected environments.',
        f'unprotected_rules = {_toml_str_list(unprotected)}',
        '',
        '[weights]',
    ]


def _weight_lines(weight_for):
    """Aligned ``rule_id = weight  # name (tag)`` lines for every rule."""
    max_id = max(len(r.id) for r in RULES)
    lines = []
    for r in sorted(RULES, key=lambda r: r.num):
        tag = 'fixable' if r.fixable else 'unfixable'
        lines.append(f'{r.id:<{max_id}} = {weight_for(r):>2}  # {r.name} ({tag})')
    return lines


def generate_default_config():
    """Return a .clat.toml string with all rules and their default weights."""
    lines = _config_lines(
        DEFAULT_THRESHOLD,
        DEFAULT_PROTECTED_ENVIRONMENTS,
        (),
    )
    lines += _weight_lines(lambda r: r.weight)
    return '\n'.join(lines) + '\n'


def save_config(config, path):
    """Write config dict back to a .clat.toml file, preserving all settings."""
    from pathlib import Path
    # Rebuild from current state, respecting weight and protection overrides.
    lines = _config_lines(
        config['threshold'],
        config.get('protected_environments', DEFAULT_PROTECTED_ENVIRONMENTS),
        config.get('unprotected_rules', ()),
    )
    lines += _weight_lines(lambda r: _effective_weight(r, config))
    Path(path).write_text('\n'.join(lines) + '\n')
    return path


# ── Environment protection ───────────────────────────────────────────
# Some environments — TikZ pictures, pgfplots axes, tikz-cd diagrams — contain
# syntax that the prose-oriented rules would happily mangle: coordinates with
# commas, periods inside node text, "100 pt" lengths, table-like rows, and so
# on.  Each such block is masked out before a rule runs and restored verbatim
# afterwards, so the rule never sees its contents.  Masking is applied per
# rule, so an individual rule can opt back in via ``unprotected_rules``.

_PROTECT_SENTINEL = _PROTECT_SENTINEL_PREFIX + '{}\x01'
_BEGIN_ANY_ENV_RE = re.compile(r'\\begin\{([^}]+)\}')


def _protected_blocks(lines, envs):
    """Yield ``(start, end)`` inclusive line-index ranges of protected blocks.

    Blocks are matched by environment name with depth counting, so a protected
    environment nested inside one of the same name is handled, and any block
    nested inside an already-protected block is absorbed into the outer one.
    Comment lines are not treated as block starts.
    """
    n = len(lines)
    i = 0
    while i < n:
        match = _BEGIN_ANY_ENV_RE.search(lines[i])
        if (match and match.group(1) in envs
                and not lines[i].lstrip().startswith('%')):
            env = match.group(1)
            beg_re = re.compile(r'\\begin\{' + re.escape(env) + r'\}')
            end_re = re.compile(r'\\end\{' + re.escape(env) + r'\}')
            depth = 0
            j = i
            while j < n:
                depth += len(beg_re.findall(lines[j]))
                depth -= len(end_re.findall(lines[j]))
                if depth <= 0:
                    break
                j += 1
            yield (i, min(j, n - 1))
            i = j + 1
        else:
            i += 1


def _mask_environments(text, envs):
    """Replace each protected environment block with a one-line sentinel.

    Returns ``(masked_text, mapping)`` where ``mapping`` is a list of
    ``(sentinel, original_block)`` pairs for restoration.
    """
    if not envs:
        return text, []
    lines = text.split('\n')
    blocks = list(_protected_blocks(lines, envs))
    if not blocks:
        return text, []
    out = []
    mapping = []
    prev_end = -1
    for start, end in blocks:
        out.extend(lines[prev_end + 1:start])
        sentinel = _PROTECT_SENTINEL.format(len(mapping))
        # Keep the first line's leading indent on the sentinel line, not in the
        # stored block, so an indentation rule re-indenting the sentinel can't
        # accumulate tabs onto the block each sweep (it would never converge).
        first = lines[start]
        indent = first[:len(first) - len(first.lstrip())]
        body = '\n'.join([first[len(indent):]] + lines[start + 1:end + 1])
        mapping.append((sentinel, body))
        out.append(indent + sentinel)
        prev_end = end
    out.extend(lines[prev_end + 1:])
    return '\n'.join(out), mapping


def _unmask_environments(text, mapping):
    """Restore the blocks masked by :func:`_mask_environments`."""
    for sentinel, original in mapping:
        text = text.replace(sentinel, original)
    return text


def _protected_line_set(text, envs):
    """Return the set of 1-based line numbers inside protected blocks."""
    if not envs:
        return set()
    lines = text.split('\n')
    protected = set()
    for start, end in _protected_blocks(lines, envs):
        protected.update(range(start + 1, end + 2))  # 1-based, inclusive
    return protected


# ── Main entry point ─────────────────────────────────────────────────

_MAX_ITER_RULE = Rule(
    0,
    'max_iter',
    'Max iterations reached before convergence',
    lambda text, filename=None: [],
    weight=10,
    fixable=False,
    order=0,
)


def _count_text_changes(original, formatted):
    orig_lines = original.split('\n')
    fmt_lines = formatted.split('\n')
    changes = sum(1 for a, b in zip(orig_lines, fmt_lines) if a != b)
    changes += abs(len(orig_lines) - len(fmt_lines))
    return changes


@dataclass
class ClatResult:
    """Result of running clat on a file.

    Attributes
    ----------
    text : str          — the (possibly modified) source text
    clangs : list[tuple] — (rule, count) for auto-fixed rules above threshold
    clunks : list[tuple] — (rule, filename, line, msg) for unfixable issues above threshold
    splats : list[tuple] — (rule, filename, line, msg) for issues below threshold
    iterations : int      — number of fixable-rule sweeps performed
    converged : bool      — True if a sweep completed with no text changes
    """
    text: str
    clangs: list = field(default_factory=list)
    clunks: list = field(default_factory=list)
    splats: list = field(default_factory=list)
    iterations: int = 0
    converged: bool = True


def texfmt(text, filename='<input>', config=None, max_iter=DEFAULT_MAX_ITER):
    """Apply formatting rules according to config.

    Returns a ClatResult with the formatted text and categorised issues.

    Fixable rules are applied repeatedly until a full sweep makes no text
    changes, or until ``max_iter`` sweeps have run. Detect-only rules are then
    evaluated once against the final text.

    """
    if max_iter < 1:
        raise ValueError('max_iter must be >= 1')

    if config is None:
        config = _default_config()

    threshold = config['threshold']
    result = ClatResult(text=text)

    # Sort rules by order for deterministic application
    sorted_rules = sorted(RULES, key=lambda r: r.order)
    fixable_rules = [r for r in sorted_rules if r.fixable]
    detect_rules = [r for r in sorted_rules if not r.fixable]
    clang_counts = {}
    fixable_splats = set()

    # Environments masked out before a rule runs (e.g. tikzpicture), unless the
    # rule is listed in ``unprotected_rules``.
    protected_envs = set(config.get('protected_environments',
                                    DEFAULT_PROTECTED_ENVIRONMENTS))
    unprotected = set(config.get('unprotected_rules', ()))

    def _respects_protection(rule):
        return bool(protected_envs) and rule.id not in unprotected

    for sweep in range(max_iter):
        sweep_start = result.text
        result.iterations = sweep + 1

        for rule in fixable_rules:
            w = _effective_weight(rule, config)
            if w <= 0:
                continue

            original = result.text
            if _respects_protection(rule):
                masked, mapping = _mask_environments(original, protected_envs)
                result.text = _unmask_environments(rule.fn(masked), mapping)
            else:
                result.text = rule.fn(original)
            if result.text == original:
                continue

            n_hits = _count_text_changes(original, result.text)
            if w >= threshold:
                clang_counts[rule.id] = clang_counts.get(rule.id, 0) + n_hits
            else:
                # Below threshold: still fix, but report as splat.
                fixable_splats.add(rule.id)

        if result.text == sweep_start:
            result.converged = True
            break
    else:
        result.converged = False

    for rule in fixable_rules:
        count = clang_counts.get(rule.id)
        if count:
            result.clangs.append((rule, count))
        if rule.id in fixable_splats:
            result.splats.append((rule, filename, 0, f'{rule.name} (auto-fixed)'))

    protected_lines = _protected_line_set(result.text, protected_envs)
    for rule in detect_rules:
        w = _effective_weight(rule, config)
        if w <= 0:
            continue
        issues = rule.fn(result.text, filename)
        if _respects_protection(rule):
            issues = [iss for iss in issues if iss[1] not in protected_lines]
        for fname, line, msg in issues:
            if w >= threshold:
                result.clunks.append((rule, fname, line, msg))
            else:
                result.splats.append((rule, fname, line, msg))

    if not result.converged and max_iter > 1:
        result.clunks.append((
            _MAX_ITER_RULE,
            filename,
            0,
            f'max iterations ({max_iter}) reached before convergence; '
            'possible rule interaction cycle',
        ))

    return result
