#!/usr/bin/env python3
"""
clat — Colin's LaTeX Tidy

Rules:
  1. Labels inline with headings: \\section{...}\\label{...}
  2. Clear % lines around equation/align environments
     (unless a paragraph break already provides separation)
  3. One sentence per line (abbreviation-safe)

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


def texfmt(text):
    """Apply all formatting rules in order."""
    text = rule1_labels_inline(text)
    text = rule2_equation_separators(text)
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
