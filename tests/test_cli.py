"""Tests for clat CLI helpers."""

from pathlib import Path

from clat.cli import discover_tex_files, _cmd_set


def test_discover_tex_files_recurses_inputs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'chapters').mkdir()
    (tmp_path / 'appendix').mkdir()
    (tmp_path / 'shared').mkdir()

    (tmp_path / 'main.tex').write_text(
        '\\input{chapters/intro}\n'
        '\\include{chapters/method}\n'
        '\\subfile{appendix/app.tex}\n'
        '% \\input{ignored}\n'
        '\\input{missing}\n'
        '\\input{not-source.sty}\n'
    )
    (tmp_path / 'chapters' / 'intro.tex').write_text(
        '\\input{../shared/defs}\n'
    )
    (tmp_path / 'chapters' / 'method.tex').write_text('Method text.\n')
    (tmp_path / 'appendix' / 'app.tex').write_text('Appendix text.\n')
    (tmp_path / 'shared' / 'defs.tex').write_text('\\input{../main}\n')

    files = discover_tex_files(['main.tex'])

    assert [Path(path) for path in files] == [
        Path('main.tex'),
        Path('chapters/intro.tex'),
        Path('shared/defs.tex'),
        Path('chapters/method.tex'),
        Path('appendix/app.tex'),
        Path('missing.tex'),
    ]


def test_cmd_set_accepts_rule_id(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    _cmd_set(['math_delimiters_equation', '5'])

    config_text = (tmp_path / '.clat.toml').read_text()
    assert 'math_delimiters_equation =  5' in config_text


def test_discover_tex_files_handles_bare_input_and_import(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'sections').mkdir()

    (tmp_path / 'main.tex').write_text(
        '\\input sections/intro\n'
        '\\import{sections/}{method}\n'
    )
    (tmp_path / 'sections' / 'intro.tex').write_text('Intro text.\n')
    (tmp_path / 'sections' / 'method.tex').write_text('Method text.\n')

    files = discover_tex_files(['main.tex'])

    assert [Path(path) for path in files] == [
        Path('main.tex'),
        Path('sections/intro.tex'),
        Path('sections/method.tex'),
    ]
