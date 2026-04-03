#!/usr/bin/env python3
"""
clat — Colin's LaTeX Tidy

Rules:
  1. Labels inline with headings: \\section{...}\\label{...}
  2. Clear % lines around equation/align environments
     (unless a paragraph break already provides separation)
  3. One sentence per line (abbreviation-safe)
  4. Equation punctuation: adds comma or period at end of display
     equations based on the following prose context
  5. Heading spacing: two blank lines before, no blank line after
  6. Figure indentation: tab-indent content inside figure environments

Usage:
  clat main.tex              # in-place
  clat main.tex -o out.tex   # write to separate file
  clat main.tex --check      # report only, no changes
"""

import argparse
import re
import sys

# Abbreviations that should not trigger sentence splitting.
# Each entry is matched case-sensitively before a period.
ABBREVIATIONS = [
    # Latin
    'e.g', 'i.e', 'cf', 'etc', 'vs', 'et al', 'viz', 'ibid',
    # Titles
    'Dr', 'Mr', 'Mrs', 'Ms', 'Prof', 'Sr', 'Jr', 'St',
    # Academic / LaTeX
    'Fig', 'Figs', 'Eq', 'Eqs', 'Ref', 'Refs', 'Sec', 'Secs',
    'Ch', 'Vol', 'vol', 'no', 'No', 'pp', 'ed', 'eds',
    'Proc', 'Trans', 'Rev',
    # Units / misc
    'approx', 'resp', 'incl',
]

# Build a regex that matches any abbreviation period we should protect.
# We match the abbreviation + '.' and replace '.' with a placeholder.
PLACEHOLDER = '\x00'  # null byte — won't appear in .tex source

def _build_protect_pattern():
    """Build compiled regex matching abbreviation periods to protect."""
    # Sort longest first to avoid partial matches
    abbrs = sorted(ABBREVIATIONS, key=len, reverse=True)
    # Escape dots within abbreviations (e.g. "e.g" -> r"e\.g")
    escaped = [re.escape(a) for a in abbrs]
    pattern = r'(?:' + '|'.join(escaped) + r')\.'
    return re.compile(pattern)

PROTECT_RE = _build_protect_pattern()


def rule1_labels_inline(text):
    """Merge \\label on the line after \\section/\\subsection onto the same line."""
    return re.sub(
        r'(\\(?:sub)*section\*?\{[^}]+\})\s*\n\s*(\\label\{[^}]+\})',
        r'\1\2',
        text,
    )


def rule2_equation_separators(text):
    """Add % separator lines around equation/align environments."""
    lines = text.split('\n')
    env_start = re.compile(r'^\s*\\begin\{(equation|align)\}')
    env_end = re.compile(r'^\s*\\end\{(equation|align)\}')

    result = []
    n = len(lines)

    for i, line in enumerate(lines):
        # Before \begin{...}: insert % if previous line is non-empty prose
        if env_start.match(line) and result:
            prev = result[-1].strip()
            if prev and prev != '%':
                result.append('%')

        result.append(line)

        # After \end{...}: insert % if next line is non-empty prose
        if env_end.match(line) and i + 1 < n:
            nxt = lines[i + 1].strip()
            if nxt and nxt != '%' and not env_start.match(lines[i + 1]):
                result.append('%')

    return '\n'.join(result)


def rule3_one_sentence_per_line(text):
    """Split sentences onto individual lines, protecting abbreviations."""
    lines = text.split('\n')
    result = []

    # Lines where we should NOT reflow (environments, commands, comments, blanks)
    skip_re = re.compile(
        r'^\s*(%|\\begin|\\end|\\item|\\paragraph|\\section|\\subsection|'
        r'\\subsubsection|\\caption|\\label|\\centering|\\includegraphics|'
        r'\\toprule|\\midrule|\\bottomrule|\\hline|\\RequirePackage|'
        r'\\usepackage|\\newcommand|\\renewcommand|\\def|\\let|\\input|'
        r'\\bibliography|\\documentclass|\\title|\\author|\\address|'
        r'\\ead|\\cortext|\\journal|\\bibliographystyle|\\addtolength|'
        r'\\Require|\\Ensure|\\Statex|\\State|\\For|\\EndFor|\\If|\\EndIf)'
    )

    in_env = 0  # Track nesting of environments we shouldn't touch

    for line in lines:
        stripped = line.strip()

        # Track environments where we don't reflow
        if re.match(r'^\s*\\begin\{(equation|align|table|tabular|figure|algorithm|'
                     r'algorithmic|abstract|keyword|frontmatter|verbatim|lstlisting)\}', line):
            in_env += 1
        if re.match(r'^\s*\\end\{(equation|align|table|tabular|figure|algorithm|'
                     r'algorithmic|abstract|keyword|frontmatter|verbatim|lstlisting)\}', line):
            in_env = max(0, in_env - 1)
            result.append(line)
            continue

        # Skip non-prose lines
        if in_env or not stripped or stripped == '%' or skip_re.match(stripped):
            result.append(line)
            continue

        # Protect abbreviation periods
        protected = PROTECT_RE.sub(lambda m: m.group(0)[:-1] + PLACEHOLDER, line)

        # Split on '. ' followed by an uppercase letter (sentence boundary)
        parts = re.split(r'\.(\s+)(?=[A-Z])', protected)

        # Reassemble: parts alternate [text, whitespace, text, whitespace, ...]
        sentences = []
        i = 0
        while i < len(parts):
            if i + 1 < len(parts) and re.match(r'^\s+$', parts[i + 1]):
                sentences.append(parts[i] + '.')
                i += 2  # skip the whitespace part
            else:
                sentences.append(parts[i])
                i += 1

        # Restore protected periods and emit
        for s in sentences:
            restored = s.replace(PLACEHOLDER, '.')
            if restored.strip():
                result.append(restored)

    return '\n'.join(result)


# Words that indicate the sentence continues after the equation (→ comma).
CONTINUATION_WORDS = re.compile(
    r'^(?:where|with|for|in\s+which|such\s+that|so\s+that|and|here|'
    r'noting|since|because|if|as|giving|yielding|from\s+which|'
    r'subject\s+to|provided|assuming|respectively)\b',
    re.IGNORECASE,
)


def rule4_equation_punctuation(text):
    """Add trailing punctuation to display equations based on context."""
    lines = text.split('\n')
    env_end = re.compile(r'^\s*\\end\{(equation|align)\}\*?')
    result = list(lines)  # work on a copy
    n = len(result)

    for i in range(n):
        if not env_end.match(result[i]):
            continue

        # Find the math content line: walk back past \end, blank, %
        # A line may contain both math and \label — handle inline labels
        math_line = None
        math_idx = None
        for j in range(i - 1, -1, -1):
            s = result[j].strip()
            if s == '%' or s == '' or s.startswith('\\end{'):
                continue
            # Pure \label line — skip and keep looking
            if re.match(r'^\\label\{[^}]+\}$', s):
                continue
            math_line = result[j]
            math_idx = j
            break

        if math_idx is None:
            continue

        # Already punctuated?
        content = math_line.rstrip()
        # Strip trailing LaTeX noise: \label{...}, \\, \nonumber, \notag
        bare = re.sub(r'\s*\\label\{[^}]+\}\s*$', '', content)
        bare = re.sub(r'\s*(?:\\\\|\\nonumber|\\notag)\s*$', '', bare)
        # Strip \boxed{...} closing brace if present
        bare = re.sub(r'\}$', '', bare) if '\\boxed' in content else bare
        bare = bare.rstrip()
        if bare and bare[-1] in '.,;:':
            continue  # already has punctuation

        # Find next prose line after \end{...}
        next_prose = None
        for k in range(i + 1, n):
            s = result[k].strip()
            if s == '' or s == '%':
                continue
            next_prose = s
            break

        if next_prose is None:
            # End of file after equation → period
            punct = '.'
        elif next_prose.startswith('\\begin{'):
            # Another environment follows — likely needs comma
            punct = ','
        elif CONTINUATION_WORDS.match(next_prose):
            punct = ','
        elif next_prose[0].islower():
            # Lowercase start → sentence continues
            punct = ','
        elif next_prose[0].isupper():
            # Uppercase start → new sentence
            punct = '.'
        else:
            # LaTeX command, macro, etc. — skip
            continue

        # Insert punctuation before trailing \label{}, \\, \nonumber, \notag
        trail_match = re.search(
            r'(\s*(?:\\label\{[^}]+\}|\\\\|\\nonumber|\\notag)\s*)$', content)
        if trail_match:
            ins = trail_match.start()
            result[math_idx] = content[:ins] + punct + content[ins:]
        else:
            result[math_idx] = content + punct

    return '\n'.join(result)


def rule5_heading_spacing(text):
    """Ensure two blank lines before headings, no blank line after."""
    lines = text.split('\n')
    heading_re = re.compile(r'^\s*\\(?:sub)*section\*?\{')
    result = []

    for i, line in enumerate(lines):
        if heading_re.match(line):
            # Remove all trailing blank lines from result (we'll add exactly two)
            while result and result[-1].strip() == '':
                result.pop()
            # Don't add blank lines before the very first content line
            if result:
                result.append('')
                result.append('')
            result.append(line)
            continue

        # Skip blank line immediately after a heading (with possible \label)
        if i > 0 and line.strip() == '':
            # Walk back to see if previous non-empty line was a heading
            prev_idx = len(result) - 1
            while prev_idx >= 0 and result[prev_idx].strip() == '':
                prev_idx -= 1
            if prev_idx >= 0 and heading_re.match(result[prev_idx]):
                continue  # swallow blank line after heading

        result.append(line)

    return '\n'.join(result)


def rule6_figure_indentation(text):
    """Tab-indent content inside figure (and table) environments."""
    lines = text.split('\n')
    result = []
    env_re_open = re.compile(r'^\s*\\begin\{(figure|table)\}')
    env_re_close = re.compile(r'^\s*\\end\{(figure|table)\}')
    depth = 0

    for line in lines:
        stripped = line.strip()

        # \end line: dedent, then output at outer level
        if depth > 0 and env_re_close.match(line):
            depth -= 1
            result.append('\t' * depth + stripped if depth > 0 else stripped)
            continue

        if depth > 0:
            if not stripped:
                # Blank line — preserve
                result.append(line)
            elif line.startswith('\t'):
                # Already has tab indentation — just ensure minimum depth
                existing_tabs = len(line) - len(line.lstrip('\t'))
                if existing_tabs < depth:
                    result.append('\t' * depth + line.lstrip('\t'))
                else:
                    result.append(line)
            else:
                # Has space indentation — prefix with tab, keep relative spaces
                leading = len(line) - len(line.lstrip())
                if leading > 0:
                    result.append('\t' * depth + line)
                else:
                    result.append('\t' * depth + stripped)
        else:
            result.append(line)

        # \begin line: increase depth for subsequent lines
        if env_re_open.match(line):
            depth += 1

    return '\n'.join(result)


def texfmt(text):
    """Apply all formatting rules in order."""
    text = rule1_labels_inline(text)
    text = rule5_heading_spacing(text)
    text = rule2_equation_separators(text)
    text = rule4_equation_punctuation(text)
    text = rule6_figure_indentation(text)
    text = rule3_one_sentence_per_line(text)
    return text


def main():
    parser = argparse.ArgumentParser(description='Format LaTeX source.')
    parser.add_argument('file', help='Input .tex file')
    parser.add_argument('-o', '--output', help='Output file (default: in-place)')
    parser.add_argument('--check', action='store_true',
                        help='Report whether changes are needed, without writing')
    args = parser.parse_args()

    with open(args.file, 'r') as f:
        original = f.read()

    formatted = texfmt(original)

    if args.check:
        if original == formatted:
            print(f'{args.file}: OK')
            sys.exit(0)
        else:
            print(f'{args.file}: needs formatting')
            sys.exit(1)

    outpath = args.output or args.file
    with open(outpath, 'w') as f:
        f.write(formatted)

    if original != formatted:
        print(f'{args.file}: formatted')
    else:
        print(f'{args.file}: already clean')


if __name__ == '__main__':
    main()
