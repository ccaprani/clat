"""Optional compilation regression tests (requires a LaTeX installation)."""

import shutil
import subprocess

import pytest

from clat.cli import _cmd_format


@pytest.mark.skipif(shutil.which('pdflatex') is None, reason='pdflatex not installed')
def test_recursive_format_keeps_table_dimensions_compilable(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'main.tex').write_text(
        '\\documentclass{article}\n'
        '\\usepackage{array}\n'
        '\\begin{document}\n'
        '\\input{chapter}\n'
        '\\end{document}\n'
    )
    (tmp_path / 'chapter.tex').write_text('\n'.join((
        r'\newcolumntype{L}{>{\raggedright\arraybackslash}p{3.0cm}}',
        r'\begin{tabular}{Lp{3.4cm}}',
        r'100 kN & 60mm \\',
        r'\multicolumn{2}{p{6.4cm}}{A load of 200 kN} \\',
        r'\end{tabular}',
        r'\begin{tabular*}{12cm}{p{3cm}m{2cm}b{2cm}}',
        r'100 kN & 60mm & 20 cm \\',
        r'\end{tabular*}',
    )))

    _cmd_format(['-r', 'main.tex'])
    _cmd_format(['--check', '-r', 'main.tex'])
    result = subprocess.run(
        ['pdflatex', '-interaction=nonstopmode', '-halt-on-error', 'main.tex'],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / 'main.pdf').exists()
