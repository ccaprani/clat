"""
clat CLI — somewhere between a clang and a splat.

That sensation when you're looking at bad LaTeX source.

Issues come in three flavours:
  clang — auto-fixed
  clunk — clat bashed into something immovable; needs your attention
  splat — advisory; take it or leave it

Usage:
  clat file.tex [file2.tex ...]    Format files
  clat --check file.tex            Dry run
  clat list                        List rules, weights, and categories
  clat set <rule#> <weight>        Set a rule weight in .clat.toml
  clat set --threshold N           Set the threshold
  clat set --init                  Create .clat.toml with defaults
  clat set --reset                 Restore .clat.toml to defaults
"""

import sys
from pathlib import Path

from rich.console import Console
from rich.text import Text

from . import __version__
from .rules import (
    texfmt, load_config, save_config, generate_default_config,
    RULES, DEFAULT_THRESHOLD, _effective_weight, _get_rule_by_num,
)
from .personality import (
    GREETINGS, CLEAN, FIXED, CLUNK_INTROS, SPLAT_INTROS,
    CHECK_DIRTY, GOODBYES,
    pick, clang_or_clangs, clunk_or_clunks, splat_or_splats, fix_or_fixes,
)

console = Console(stderr=True)


# ── Helpers ──────────────────────────────────────────────────────────

def _config_path(config_arg=None):
    if config_arg:
        return Path(config_arg)
    return Path.cwd() / '.clat.toml'


def _count_changes(original, formatted):
    orig_lines = original.split('\n')
    fmt_lines = formatted.split('\n')
    changes = sum(1 for a, b in zip(orig_lines, fmt_lines) if a != b)
    changes += abs(len(orig_lines) - len(fmt_lines))
    return changes


def _print_header():
    greeting = pick(GREETINGS)
    console.print(
        Text.assemble(
            ('clat ', 'bold'),
            (f'v{__version__} ', 'dim'),
            (greeting, 'italic'),
        )
    )


def _print_issues(issues, intros, style):
    for item in issues:
        if len(item) == 4:
            rule, fname, line, msg = item
        else:
            fname, line, msg = item
        intro = pick(intros)
        loc = f'{fname}:{line}: ' if line > 0 else f'{fname}: '
        console.print(
            Text.assemble(
                (f'    {intro} ', f'bold {style}'),
                (loc, 'dim'),
                (msg, ''),
            )
        )


def _tally_issues(issues):
    """Return (n_rules, n_occurrences) for a list of issue tuples."""
    rules = {item[0].id for item in issues}
    return len(rules), len(issues)


def _times(n):
    return "time" if n == 1 else "times"


def _report(filename, result):
    n_clangs = len(result.clangs)
    n_clunks_rules, n_clunks_hits = _tally_issues(result.clunks)
    n_splats_rules, n_splats_hits = _tally_issues(result.splats)

    if n_clangs == 0 and n_clunks_rules == 0 and n_splats_rules == 0:
        console.print(f'  [green]{filename}[/]: {pick(CLEAN)}')
        return

    parts = []
    if n_clangs > 0:
        clang_hits = sum(count for _, count in result.clangs)
        msg = pick(FIXED, n=n_clangs, noun=fix_or_fixes(n_clangs))
        parts.append(f'[bold cyan]{msg} ({clang_hits} {_times(clang_hits)})[/]')
    if n_clunks_rules > 0:
        parts.append(
            f'[bold red]{n_clunks_rules} {clunk_or_clunks(n_clunks_rules)}'
            f' ({n_clunks_hits} {_times(n_clunks_hits)})[/]')
    if n_splats_rules > 0:
        parts.append(
            f'[bold yellow]{n_splats_rules} {splat_or_splats(n_splats_rules)}'
            f' ({n_splats_hits} {_times(n_splats_hits)})[/]')

    console.print(f'  {filename}: {", ".join(parts)}')
    _print_issues(result.clunks, CLUNK_INTROS, 'red')
    _print_issues(result.splats, SPLAT_INTROS, 'yellow')


def _report_check(filename, result, n_fixable):
    n_clunks_rules, n_clunks_hits = _tally_issues(result.clunks)
    n_splats_rules, n_splats_hits = _tally_issues(result.splats)

    if n_fixable == 0 and n_clunks_rules == 0 and n_splats_rules == 0:
        console.print(f'  [green]{filename}[/]: {pick(CLEAN)}')
        return

    parts = []
    if n_fixable > 0:
        clang_hits = sum(count for _, count in result.clangs)
        msg = pick(CHECK_DIRTY, n=n_fixable,
                   noun=clang_or_clangs(n_fixable))
        parts.append(f'[bold red]{msg} ({clang_hits} {_times(clang_hits)})[/]')
    if n_clunks_rules > 0:
        parts.append(
            f'[bold red]{n_clunks_rules} {clunk_or_clunks(n_clunks_rules)}'
            f' ({n_clunks_hits} {_times(n_clunks_hits)})[/]')
    if n_splats_rules > 0:
        parts.append(
            f'[bold yellow]{n_splats_rules} {splat_or_splats(n_splats_rules)}'
            f' ({n_splats_hits} {_times(n_splats_hits)})[/]')

    console.print(f'  {filename}: {", ".join(parts)}')
    _print_issues(result.clunks, CLUNK_INTROS, 'red')
    _print_issues(result.splats, SPLAT_INTROS, 'yellow')


def _print_goodbye():
    console.print(Text(pick(GOODBYES), style='dim'))


# ── clat list ────────────────────────────────────────────────────────

def _cmd_list(argv):
    """List all rules with numbers, weights, and categories."""
    import argparse
    parser = argparse.ArgumentParser(
        prog='clat list', description='List all rules')
    parser.add_argument('--config', help='Path to .clat.toml')
    args = parser.parse_args(argv)

    config = load_config(args.config)
    threshold = config['threshold']

    _print_header()
    console.print(f'  [bold]threshold = {threshold}[/]\n')

    for r in sorted(RULES, key=lambda r: r.num):
        w = _effective_weight(r, config)
        if w >= threshold and r.fixable:
            cat, style = 'clang', 'bold cyan'
        elif w >= threshold and not r.fixable:
            cat, style = 'clunk', 'bold red'
        else:
            cat, style = 'splat', 'bold yellow'
        fix_tag = '✓' if r.fixable else '✗'
        console.print(
            f'  {fix_tag} {r.num:>2}: [{style}]{cat:>5}[/]  '
            f'w={w:<2}  {r.name}'
        )

    _print_goodbye()


# ── clat set ─────────────────────────────────────────────────────────

def _cmd_set(argv):
    """Handle `clat set ...` subcommand."""
    import argparse
    parser = argparse.ArgumentParser(
        prog='clat set',
        description='Configure rules and threshold in .clat.toml',
    )
    parser.add_argument('rule_num', nargs='?', type=int,
                        help='Rule number (see clat list)')
    parser.add_argument('weight', nargs='?', type=int,
                        help='Weight to assign (1–10)')
    parser.add_argument('--threshold', type=int, default=None,
                        help='Set the threshold (1–10)')
    parser.add_argument('--init', action='store_true',
                        help='Create .clat.toml with defaults')
    parser.add_argument('--reset', action='store_true',
                        help='Reset .clat.toml to defaults')
    parser.add_argument('--config', help='Path to .clat.toml')
    args = parser.parse_args(argv)

    dest = _config_path(args.config)

    if args.reset:
        dest.write_text(generate_default_config())
        console.print(f'[green]Reset[/] {dest} to defaults')
        return

    if args.init:
        if dest.exists():
            console.print(
                f'[bold yellow]{dest}[/] already exists. '
                f'Use [bold]clat set --reset[/] to restore defaults.')
            sys.exit(1)
        dest.write_text(generate_default_config())
        console.print(f'[green]Created[/] {dest}')
        return

    config = load_config(args.config)

    if args.threshold is not None:
        config['threshold'] = args.threshold
        save_config(config, dest)
        console.print(f'[green]Set[/] threshold = {args.threshold} in {dest}')
        return

    if args.rule_num is not None and args.weight is not None:
        rule = _get_rule_by_num(args.rule_num)
        if rule is None:
            console.print(
                f'[bold red]Unknown rule:[/] {args.rule_num}\n'
                f'  Run [bold]clat list[/] to see available rules.')
            sys.exit(1)
        config['weights'][rule.id] = args.weight
        save_config(config, dest)
        w = args.weight
        threshold = config['threshold']
        if w >= threshold and rule.fixable:
            cat = 'clang'
        elif w >= threshold:
            cat = 'clunk'
        else:
            cat = 'splat'
        console.print(
            f'[green]Set[/] rule {rule.num} ({rule.name}) = {w} ({cat}) '
            f'in {dest}')
        return

    parser.print_help()
    sys.exit(1)


# ── clat (format) ────────────────────────────────────────────────────

def _cmd_format(argv):
    import argparse
    parser = argparse.ArgumentParser(
        prog='clat',
        description="Colin's LaTeX Tidy — somewhere between a clang and a splat.",
    )
    parser.add_argument('files', nargs='*', help='.tex files to format')
    parser.add_argument('-o', '--output',
                        help='Output file (single input only)')
    parser.add_argument('--check', action='store_true',
                        help='Report without fixing')
    parser.add_argument('--config', help='Path to .clat.toml')
    parser.add_argument('--threshold', type=int, default=None,
                        help='Override threshold for this run')
    parser.add_argument('--version', action='version',
                        version=f'clat {__version__}')
    args = parser.parse_args(argv)

    if args.output and len(args.files) > 1:
        parser.error('-o/--output only works with a single input file')

    config = load_config(args.config)
    if args.threshold is not None:
        config['threshold'] = args.threshold

    if not args.files:
        parser.error('no .tex files specified')

    _print_header()

    any_issues = False

    for filepath in args.files:
        try:
            with open(filepath, 'r') as f:
                original = f.read()
        except FileNotFoundError:
            console.print(f'  [bold red]CLANG[/] {filepath}: file not found')
            any_issues = True
            continue

        result = texfmt(original, filename=filepath, config=config)
        n_fixes = _count_changes(original, result.text)

        if args.check:
            _report_check(filepath, result, n_fixes)
            if n_fixes > 0 or result.clunks or result.splats:
                any_issues = True
        else:
            outpath = args.output or filepath
            if result.text != original:
                with open(outpath, 'w') as f:
                    f.write(result.text)
            _report(filepath, result)
            if result.clunks or result.splats:
                any_issues = True

    _print_goodbye()
    if any_issues:
        sys.exit(1)


# ── Entry point ──────────────────────────────────────────────────────

def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == 'set':
            _cmd_set(sys.argv[2:])
            return
        if cmd == 'list':
            _cmd_list(sys.argv[2:])
            return
    _cmd_format(sys.argv[1:])


if __name__ == '__main__':
    main()
