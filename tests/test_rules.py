"""Tests for clat formatting rules."""

import os
import pytest

from clat.rules import (
    rule1_labels_inline,
    rule2_equation_separators,
    rule3_one_sentence_per_line,
    rule4_equation_punctuation,
    rule5_heading_spacing,
    rule6_figure_indentation,
    rule7_strip_decorative_comments,
    rule8_math_delimiters_inline,
    rule9_math_delimiters_display,
    rule10_math_delimiters_equation,
    rule11_tilde_before_refs,
    rule12_number_unit_spacing,
    rule13_old_font_commands,
    rule14_ellipsis,
    rule15_ordinal_suffixes,
    rule16_table_line_endings,
    rule17_abbreviation_spacing,
    warn_hardcoded_refs,
    warn_manual_sizing,
    warn_long_file,
    warn_float_after_heading,
    texfmt,
    ClatResult,
    RULES,
    Rule,
    DEFAULT_THRESHOLD,
    DEFAULT_MAX_ITER,
    _effective_weight,
    _get_rule,
)

TESTS_DIR = os.path.dirname(__file__)


# ── Integration test: full pipeline against golden file ──────────────

class TestGoldenFile:
    def test_full_pipeline(self):
        with open(os.path.join(TESTS_DIR, 'input.tex')) as f:
            source = f.read()
        with open(os.path.join(TESTS_DIR, 'expected.tex')) as f:
            expected = f.read()
        result = texfmt(source, 'input.tex')
        assert result.text == expected

    def test_idempotent(self):
        with open(os.path.join(TESTS_DIR, 'expected.tex')) as f:
            expected = f.read()
        result = texfmt(expected, 'expected.tex')
        assert result.text == expected


# ── Rule 1: labels inline ───────────────────────────────────────────

class TestRule1:
    def test_section_label_merge(self):
        src = '\\section{Foo}\n\\label{sec:foo}'
        assert rule1_labels_inline(src) == '\\section{Foo}\\label{sec:foo}'

    def test_subsection_label_merge(self):
        src = '\\subsection{Bar}\n  \\label{sec:bar}'
        assert rule1_labels_inline(src) == '\\subsection{Bar}\\label{sec:bar}'

    def test_already_inline(self):
        src = '\\section{Foo}\\label{sec:foo}'
        assert rule1_labels_inline(src) == src

    def test_no_label(self):
        src = '\\section{Foo}\nSome text.'
        assert rule1_labels_inline(src) == src


# ── Rule 2: equation separators ─────────────────────────────────────

class TestRule2:
    def test_percent_before_equation(self):
        src = 'Some text.\n\\begin{equation}\nx\n\\end{equation}'
        result = rule2_equation_separators(src)
        lines = result.split('\n')
        assert lines[1] == '%'
        assert lines[2] == '\\begin{equation}'

    def test_no_double_percent(self):
        src = 'Some text.\n%\n\\begin{equation}\nx\n\\end{equation}'
        result = rule2_equation_separators(src)
        assert result.count('\n%\n%\n') == 0

    def test_blank_line_around_figure(self):
        src = 'Some text.\n\\begin{figure}\nfoo\n\\end{figure}\nMore text.'
        result = rule2_equation_separators(src)
        lines = result.split('\n')
        assert lines[1] == ''
        assert lines[2] == '\\begin{figure}'

    def test_subequations_separator_wraps_outer_env(self):
        src = (
            'The corresponding natural frequencies are given by:\n'
            '\\begin{subequations}\n'
            '%\n'
            '    \\begin{align}\n'
            '        x &= y \\\\\n'
            '        z &= w.\n'
            '    \\end{align}\n'
            '%\n'
            '\\end{subequations}\n'
            'Next sentence.'
        )
        expected = (
            'The corresponding natural frequencies are given by:\n'
            '%\n'
            '\\begin{subequations}\n'
            '    \\begin{align}\n'
            '        x &= y \\\\\n'
            '        z &= w.\n'
            '    \\end{align}\n'
            '\\end{subequations}\n'
            '%\n'
            'Next sentence.'
        )
        assert rule2_equation_separators(src) == expected

    def test_starred_math_env_separator(self):
        src = 'Some text.\n\\begin{align*}\nx &= y\n\\end{align*}\nMore text.'
        expected = 'Some text.\n%\n\\begin{align*}\nx &= y\n\\end{align*}\n%\nMore text.'
        assert rule2_equation_separators(src) == expected


# ── Rule 3: one sentence per line ───────────────────────────────────

class TestRule3:
    def test_split_sentences(self):
        src = 'First sentence. Second sentence.'
        result = rule3_one_sentence_per_line(src)
        assert result == 'First sentence.\nSecond sentence.'

    def test_protect_abbreviation(self):
        src = 'See Fig. 3 for details.'
        result = rule3_one_sentence_per_line(src)
        assert result == src  # no split

    def test_skip_commands(self):
        src = '\\begin{equation}\nA. B.\n\\end{equation}'
        result = rule3_one_sentence_per_line(src)
        assert result == src


# ── Rule 4: equation punctuation ────────────────────────────────────

class TestRule4:
    def test_comma_before_where(self):
        src = '\\begin{equation}\nF = ma\n\\end{equation}\nwhere'
        result = rule4_equation_punctuation(src)
        assert 'F = ma,' in result

    def test_period_before_uppercase(self):
        src = '\\begin{equation}\nE = mc^2\n\\end{equation}\nThe energy'
        result = rule4_equation_punctuation(src)
        assert 'E = mc^2.' in result

    def test_already_punctuated(self):
        src = '\\begin{equation}\nF = ma.\n\\end{equation}\nThe force'
        result = rule4_equation_punctuation(src)
        assert result.count('.') == 1  # no double punctuation


# ── Rule 5: heading spacing ─────────────────────────────────────────

class TestRule5:
    def test_two_blanks_before(self):
        src = 'Some text.\n\\section{Foo}'
        result = rule5_heading_spacing(src)
        lines = result.split('\n')
        assert lines[1] == ''
        assert lines[2] == ''
        assert lines[3] == '\\section{Foo}'

    def test_no_blanks_between_consecutive_headings(self):
        src = '\\section{Intro}\n\n\n\\subsection{Background}'
        result = rule5_heading_spacing(src)
        lines = result.split('\n')
        assert lines == ['\\section{Intro}', '\\subsection{Background}']

    def test_no_blank_after(self):
        src = '\\section{Foo}\n\nSome text.'
        result = rule5_heading_spacing(src)
        lines = result.split('\n')
        idx = lines.index('\\section{Foo}')
        assert lines[idx + 1] == 'Some text.'


# ── Rule 6: indentation ─────────────────────────────────────────────

class TestRule6:
    def test_figure_indent(self):
        src = '\\begin{figure}\n\\centering\n\\end{figure}'
        result = rule6_figure_indentation(src)
        assert '\t\\centering' in result

    def test_itemize_indent(self):
        src = '\\begin{itemize}\n\\item Foo.\n\\end{itemize}'
        result = rule6_figure_indentation(src)
        assert '\t\\item Foo.' in result

    def test_enumerate_indent(self):
        src = '\\begin{enumerate}\n\\item Bar.\n\\end{enumerate}'
        result = rule6_figure_indentation(src)
        assert '\t\\item Bar.' in result

    def test_nested(self):
        src = '\\begin{figure}\n\\begin{itemize}\n\\item X.\n\\end{itemize}\n\\end{figure}'
        result = rule6_figure_indentation(src)
        assert '\t\t\\item X.' in result


# ── Rule 7: decorative comments ─────────────────────────────────────

class TestRule7:
    def test_strip_equals(self):
        src = 'text\n%% ========\nmore'
        assert '====' not in rule7_strip_decorative_comments(src)

    def test_strip_dashes(self):
        src = 'text\n% ------\nmore'
        assert '----' not in rule7_strip_decorative_comments(src)

    def test_strip_stars(self):
        src = 'text\n%% ****\nmore'
        assert '****' not in rule7_strip_decorative_comments(src)

    def test_keep_normal_comment(self):
        src = '% This is a comment'
        assert rule7_strip_decorative_comments(src) == src


# ── Rule 8: inline math delimiters ──────────────────────────────────

class TestRule8:
    def test_inline_paren(self):
        src = 'The value \\(x\\) is positive.'
        assert rule8_math_delimiters_inline(src) == 'The value $x$ is positive.'

    def test_display_bracket_left_alone(self):
        src = '\\[E = mc^2\\]'
        assert rule8_math_delimiters_inline(src) == src

    def test_dollars_left_alone(self):
        src = 'costs \\$5 and $y = mx + b$'
        assert rule8_math_delimiters_inline(src) == src

    def test_skip_comments(self):
        src = '% \\(x\\) in a comment'
        assert rule8_math_delimiters_inline(src) == src

    def test_idempotent(self):
        src = 'Already $x$ and $$y$$.'
        assert rule8_math_delimiters_inline(src) == src


# ── Rule 9: display math delimiters ─────────────────────────────────

class TestRule9:
    def test_display_bracket(self):
        src = '\\[E = mc^2\\]'
        assert rule9_math_delimiters_display(src) == '$$E = mc^2$$'

    def test_multiline_display(self):
        src = '\\[\n  a = b\n\\]'
        assert rule9_math_delimiters_display(src) == '$$\n  a = b\n$$'

    def test_inline_paren_left_alone(self):
        src = 'The value \\(x\\) is positive.'
        assert rule9_math_delimiters_display(src) == src

    def test_idempotent(self):
        src = 'Already $x$ and $$y$$.'
        assert rule9_math_delimiters_display(src) == src


# ── Rule 10: display math delimiters to equation ────────────────────

class TestRule10:
    def test_display_bracket_single_line(self):
        src = '\\[E = mc^2\\]'
        assert rule10_math_delimiters_equation(src) == (
            '\\begin{equation}\nE = mc^2\n\\end{equation}'
        )

    def test_display_bracket_multiline(self):
        src = '\\[\n  a = b\n\\]'
        assert rule10_math_delimiters_equation(src) == (
            '\\begin{equation}\n  a = b\n\\end{equation}'
        )

    def test_double_dollar_single_line(self):
        src = '$$E = mc^2$$'
        assert rule10_math_delimiters_equation(src) == (
            '\\begin{equation}\nE = mc^2\n\\end{equation}'
        )

    def test_double_dollar_multiline(self):
        src = '$$\n  a = b\n$$'
        assert rule10_math_delimiters_equation(src) == (
            '\\begin{equation}\n  a = b\n\\end{equation}'
        )

    def test_inline_prose_left_alone(self):
        src = 'before \\[x\\] after and before $$y$$ after'
        assert rule10_math_delimiters_equation(src) == src

    def test_skip_comments(self):
        src = '% \\[x\\]\n\\[y\\]'
        assert rule10_math_delimiters_equation(src) == (
            '% \\[x\\]\n\\begin{equation}\ny\n\\end{equation}'
        )

    def test_skip_verbatim(self):
        src = '\\begin{verbatim}\n\\[x\\]\n\\end{verbatim}\n$$y$$'
        assert rule10_math_delimiters_equation(src) == (
            '\\begin{verbatim}\n\\[x\\]\n\\end{verbatim}\n'
            '\\begin{equation}\ny\n\\end{equation}'
        )


# ── Rule 11: tilde before refs ──────────────────────────────────────

class TestRule11:
    def test_space_before_cref(self):
        src = 'see \\cref{sec:foo}'
        assert rule11_tilde_before_refs(src) == 'see~\\cref{sec:foo}'

    def test_space_before_ref(self):
        src = 'in \\ref{eq:one}'
        assert rule11_tilde_before_refs(src) == 'in~\\ref{eq:one}'

    def test_space_before_cite(self):
        src = 'shown \\cite{smith2020}'
        assert rule11_tilde_before_refs(src) == 'shown~\\cite{smith2020}'

    def test_already_tilde(self):
        src = 'see~\\cref{sec:foo}'
        assert rule11_tilde_before_refs(src) == src


# ── Rule 12: number-unit spacing ────────────────────────────────────

class TestRule12:
    def test_tilde_to_thinspace(self):
        assert rule12_number_unit_spacing('100~kN') == '100\\,kN'

    def test_space_to_thinspace(self):
        assert rule12_number_unit_spacing('34 m/s') == '34\\,m/s'

    def test_no_false_positive(self):
        src = 'the 10 methods'
        assert rule12_number_unit_spacing(src) == src

    def test_mm(self):
        assert rule12_number_unit_spacing('60 mm') == '60\\,mm'

    def test_already_thinspace(self):
        assert rule12_number_unit_spacing('100\\,kN') == '100\\,kN'

    def test_no_space_to_thinspace(self):
        assert rule12_number_unit_spacing('100kN') == '100\\,kN'

    def test_latex_spacing_to_thinspace(self):
        assert rule12_number_unit_spacing('100\\;kN and 200\\quad kN') == \
            '100\\,kN and 200\\,kN'

    def test_no_space_bare_seconds_skipped(self):
        assert rule12_number_unit_spacing('the 1990s') == 'the 1990s'

    def test_dollar_number_tilde(self):
        assert rule12_number_unit_spacing('$78$~kN') == '$78$\\,kN'

    def test_dollar_number_space(self):
        assert rule12_number_unit_spacing('$78$ kN') == '$78$\\,kN'

    def test_dollar_number_no_space(self):
        assert rule12_number_unit_spacing('$78$kN') == '$78$\\,kN'

    def test_dollar_expression_space(self):
        assert rule12_number_unit_spacing('$EI = 200$ MN') == '$EI = 200$\\,MN'

    def test_dollar_expression_no_space(self):
        assert rule12_number_unit_spacing('$EI = 200$MN') == '$EI = 200$\\,MN'

    def test_dollar_subscript_space(self):
        assert rule12_number_unit_spacing(r'$\mu_P^{\text{true}} = 78$ kN') \
            == r'$\mu_P^{\text{true}} = 78$\,kN'

    def test_dollar_already_thinspace(self):
        assert rule12_number_unit_spacing('$5$\\,kN') == '$5$\\,kN'

    def test_dollar_non_numeric_skipped(self):
        # "$x$ kN" would be odd; the content doesn't end in a digit/brace
        # so no substitution occurs and the line is left alone.
        assert rule12_number_unit_spacing('$x$ kN') == '$x$ kN'


# ── Rule 13: old font commands ──────────────────────────────────────

class TestRule13:
    def test_bf(self):
        assert rule13_old_font_commands('{\\bf bold}') == '\\textbf{bold}'

    def test_it(self):
        assert rule13_old_font_commands('{\\it italic}') == '\\textit{italic}'

    def test_em(self):
        assert rule13_old_font_commands('{\\em emph}') == '\\emph{emph}'

    def test_tt(self):
        assert rule13_old_font_commands('{\\tt code}') == '\\texttt{code}'

    def test_no_match(self):
        src = '\\textbf{already modern}'
        assert rule13_old_font_commands(src) == src


# ── Rule 14: ellipsis ───────────────────────────────────────────────

class TestRule14:
    def test_triple_dot(self):
        assert rule14_ellipsis('and so on...') == 'and so on\\dots'

    def test_already_dots(self):
        src = 'and so on\\dots'
        assert rule14_ellipsis(src) == src

    def test_skip_comment(self):
        src = '% text...'
        assert rule14_ellipsis(src) == src


# ── Rule 15: ordinal suffixes ───────────────────────────────────────

class TestRule15:
    def test_textsuperscript_ordinal(self):
        assert rule15_ordinal_suffixes(r'the 1\textsuperscript{st} DOF') == 'the 1st DOF'

    def test_inline_math_ordinal(self):
        assert rule15_ordinal_suffixes(r'the $2^{\text{nd}}$ DOF') == 'the 2nd DOF'

    def test_split_inline_math_ordinal(self):
        assert rule15_ordinal_suffixes(r'the 3$^{\mathrm{rd}}$ DOF') == 'the 3rd DOF'

    def test_bare_math_ordinal(self):
        assert rule15_ordinal_suffixes(r'the $4^{th}$ DOF') == 'the 4th DOF'

    def test_skip_comment(self):
        src = r'% the 1\textsuperscript{st} DOF'
        assert rule15_ordinal_suffixes(src) == src


# ── Rule 16: table line endings ─────────────────────────────────────

class TestRule16:
    def test_row_ending_moves_onto_table_row(self):
        src = '\\begin{tabular}{ll}\nA & B\n\\\\\n\\end{tabular}'
        expected = '\\begin{tabular}{ll}\nA & B \\\\\n\\end{tabular}'
        assert rule16_table_line_endings(src) == expected

    def test_horizontal_rule_kept_on_own_line(self):
        src = '\\begin{tabular}{ll}\nA & B \\\\ \\hline\nC & D\n\\end{tabular}'
        expected = '\\begin{tabular}{ll}\nA & B \\\\\n\\hline\nC & D\n\\end{tabular}'
        assert rule16_table_line_endings(src) == expected

    def test_horizontal_rule_drops_trailing_row_ending(self):
        src = '\\begin{tabular}{ll}\n\\hline \\\\\nA & B\n\\end{tabular}'
        expected = '\\begin{tabular}{ll}\n\\hline\nA & B\n\\end{tabular}'
        assert rule16_table_line_endings(src) == expected


# ── Rule 17: abbreviation spacing ───────────────────────────────────

class TestRule17:
    def test_eg_before_lowercase(self):
        assert rule17_abbreviation_spacing('use a tool, e.g. clat here') \
            == 'use a tool, e.g.\\ clat here'

    def test_ie_before_lowercase(self):
        assert rule17_abbreviation_spacing('that is, i.e. the result') \
            == 'that is, i.e.\\ the result'

    def test_eg_before_capital_still_fixed(self):
        # "e.g." never ends a sentence, so a following proper noun is fixed too.
        assert rule17_abbreviation_spacing('languages, e.g. Python rules') \
            == 'languages, e.g.\\ Python rules'

    def test_cf_viz_vs_fixed(self):
        assert rule17_abbreviation_spacing('cf. Smith') == 'cf.\\ Smith'
        assert rule17_abbreviation_spacing('viz. the cases') == 'viz.\\ the cases'
        assert rule17_abbreviation_spacing('A vs. B') == 'A vs.\\ B'

    def test_et_al_before_lowercase(self):
        assert rule17_abbreviation_spacing('Smith et al. showed that') \
            == 'Smith et al.\\ showed that'

    def test_et_al_before_open_paren(self):
        assert rule17_abbreviation_spacing('Smith et al. (2020) found') \
            == 'Smith et al.\\ (2020) found'

    def test_et_al_before_capital_left_alone(self):
        # Ambiguous: "et al." may end the sentence, so a capital is untouched.
        src = 'reported by Smith et al. The next study'
        assert rule17_abbreviation_spacing(src) == src

    def test_etc_before_capital_left_alone(self):
        src = 'apples, oranges, etc. Then we conclude'
        assert rule17_abbreviation_spacing(src) == src

    def test_etc_before_lowercase(self):
        assert rule17_abbreviation_spacing('apples, etc. are available') \
            == 'apples, etc.\\ are available'

    def test_followed_by_comma_untouched(self):
        src = 'use a tool, e.g., clat'
        assert rule17_abbreviation_spacing(src) == src

    def test_already_control_space_idempotent(self):
        src = 'use a tool, e.g.\\ clat here'
        assert rule17_abbreviation_spacing(src) == src

    def test_collapses_multiple_spaces(self):
        assert rule17_abbreviation_spacing('see e.g.   the thing') \
            == 'see e.g.\\ the thing'

    def test_skips_comment_lines(self):
        src = '% e.g. a comment'
        assert rule17_abbreviation_spacing(src) == src

    def test_skips_verbatim(self):
        src = '\\begin{verbatim}\ne.g. raw text\n\\end{verbatim}'
        assert rule17_abbreviation_spacing(src) == src

    def test_not_matched_inside_word(self):
        # "revs." ends in "vs." but is part of a word — the leading letter
        # boundary stops it being treated as the "vs." abbreviation.
        src = 'engine revs. now climbing'
        assert rule17_abbreviation_spacing(src) == src


# ── Warnings (individual functions) ─────────────────────────────────

class TestWarnings:
    def test_hardcoded_figure(self):
        w = warn_hardcoded_refs('See Figure 3 for details.', 'test.tex')
        assert len(w) == 1
        assert 'Figure 3' in w[0][2]

    def test_hardcoded_table(self):
        w = warn_hardcoded_refs('Table 1 shows results.', 'test.tex')
        assert len(w) == 1

    def test_no_false_positive_cref(self):
        w = warn_hardcoded_refs('See \\cref{fig:one} for details.', 'test.tex')
        assert len(w) == 0

    def test_manual_sizing(self):
        w = warn_manual_sizing('\\bigg( \\frac{a}{b} \\bigg)', 'test.tex')
        assert len(w) == 2

    def test_long_file(self):
        short = '\n' * 100
        assert warn_long_file(short, 'test.tex') == []
        long = '\n' * 2500
        w = warn_long_file(long, 'test.tex')
        assert len(w) == 1
        assert '2501 lines' in w[0][2]

    def test_skip_comments(self):
        w = warn_hardcoded_refs('% Figure 3', 'test.tex')
        assert len(w) == 0
        w = warn_manual_sizing('% \\bigg', 'test.tex')
        assert len(w) == 0

    def test_float_after_section(self):
        src = '\\section{Foo}\\label{sec:foo}\n\n\\begin{figure}[t]\n\\end{figure}'
        w = warn_float_after_heading(src, 'test.tex')
        assert len(w) == 1
        assert 'figure' in w[0][2]

    def test_float_after_subsection(self):
        src = '\\subsection{Bar}\n\\begin{table}[h]\n\\end{table}'
        w = warn_float_after_heading(src, 'test.tex')
        assert len(w) == 1
        assert 'table' in w[0][2]

    def test_float_after_heading_with_label_and_blanks(self):
        src = '\\section{Foo}\n\\label{sec:foo}\n\n\\begin{figure}[t]\n\\end{figure}'
        w = warn_float_after_heading(src, 'test.tex')
        assert len(w) == 1

    def test_no_warning_when_text_between(self):
        src = '\\section{Foo}\nSome introductory text.\n\\begin{figure}[t]\n\\end{figure}'
        w = warn_float_after_heading(src, 'test.tex')
        assert len(w) == 0

    def test_algorithm_after_heading(self):
        src = '\\subsection{Method}\n\\begin{algorithm}[t]\n\\end{algorithm}'
        w = warn_float_after_heading(src, 'test.tex')
        assert len(w) == 1
        assert 'algorithm' in w[0][2]

    def test_no_warning_for_equation(self):
        src = '\\section{Theory}\n\\begin{equation}\nx = 1\n\\end{equation}'
        w = warn_float_after_heading(src, 'test.tex')
        assert len(w) == 0


# ── Rule registry ───────────────────────────────────────────────────

class TestRegistry:
    def test_all_rules_registered(self):
        assert len(RULES) == 21

    def test_rule_ids_unique(self):
        ids = [r.id for r in RULES]
        assert len(ids) == len(set(ids))

    def test_get_rule(self):
        r = _get_rule('labels_inline')
        assert r is not None
        assert r.fixable is True

    def test_get_rule_missing(self):
        assert _get_rule('nonexistent') is None

    def test_math_delimiter_rules_are_grouped_by_number(self):
        assert _get_rule('math_delimiters_inline').num == 8
        assert _get_rule('math_delimiters_display').num == 9
        assert _get_rule('math_delimiters_equation').num == 10
        assert _get_rule('tilde_before_refs').num == 11
        assert _get_rule('float_after_heading').num == 21

    def test_display_math_delimiters_default_off(self):
        assert _get_rule('math_delimiters_display').weight == 0

    def test_equation_math_delimiters_default_off(self):
        assert _get_rule('math_delimiters_equation').weight == 0

    def test_fixable_count(self):
        fixable = [r for r in RULES if r.fixable]
        assert len(fixable) == 17

    def test_unfixable_count(self):
        unfixable = [r for r in RULES if not r.fixable]
        assert len(unfixable) == 4


# ── Threshold / config behaviour ────────────────────────────────────

class TestThreshold:
    def test_default_threshold(self):
        assert DEFAULT_THRESHOLD == 5

    def test_default_max_iter(self):
        assert DEFAULT_MAX_ITER == 5

    def test_high_weight_fixable_is_clang(self):
        """A fixable rule above threshold should produce a clang."""
        src = '\\section{Foo}\n\\label{sec:foo}'
        config = {'threshold': 5, 'weights': {'labels_inline': 8}}
        result = texfmt(src, 'test.tex', config=config)
        clang_ids = [r.id for r, _ in result.clangs]
        assert 'labels_inline' in clang_ids

    def test_low_weight_fixable_is_splat(self):
        """A fixable rule below threshold should produce a splat."""
        src = '\\section{Foo}\n\\label{sec:foo}'
        config = {'threshold': 10, 'weights': {}}
        result = texfmt(src, 'test.tex', config=config)
        assert len(result.clangs) == 0
        splat_rule_ids = [item[0].id for item in result.splats
                          if hasattr(item[0], 'id')]
        assert 'labels_inline' in splat_rule_ids

    def test_high_weight_unfixable_is_clunk(self):
        """An unfixable rule above threshold should produce a clunk."""
        src = 'See Figure 3 for details.'
        config = {'threshold': 5, 'weights': {'hardcoded_refs': 8}}
        result = texfmt(src, 'test.tex', config=config)
        clunk_rule_ids = [item[0].id for item in result.clunks]
        assert 'hardcoded_refs' in clunk_rule_ids

    def test_low_weight_unfixable_is_splat(self):
        """An unfixable rule below threshold should produce a splat."""
        src = 'See Figure 3 for details.'
        config = {'threshold': 10, 'weights': {}}
        result = texfmt(src, 'test.tex', config=config)
        assert len(result.clunks) == 0
        splat_rule_ids = [item[0].id for item in result.splats
                          if hasattr(item[0], 'id')]
        assert 'hardcoded_refs' in splat_rule_ids

    def test_weight_override(self):
        """Config weight should override default."""
        r = _get_rule('ellipsis')
        assert r.weight == 4  # default
        config = {'threshold': 5, 'weights': {'ellipsis': 9}}
        assert _effective_weight(r, config) == 9

    def test_unknown_math_delimiters_key_is_ignored(self):
        config = {'threshold': 5, 'weights': {'math_delimiters': 9}}
        assert _effective_weight(_get_rule('math_delimiters_inline'), config) == 5
        assert _effective_weight(_get_rule('math_delimiters_display'), config) == 0

    def test_split_math_delimiter_weights_use_rule_ids(self):
        config = {
            'threshold': 5,
            'weights': {
                'math_delimiters_inline': 9,
                'math_delimiters_display': 0,
                'math_delimiters_equation': 5,
            },
        }
        assert _effective_weight(_get_rule('math_delimiters_inline'), config) == 9
        assert _effective_weight(_get_rule('math_delimiters_display'), config) == 0
        assert _effective_weight(_get_rule('math_delimiters_equation'), config) == 5

    def test_text_still_fixed_below_threshold(self):
        """Fixable rules below threshold should still fix the text."""
        src = '\\section{Foo}\n\\label{sec:foo}'
        config = {'threshold': 10, 'weights': {}}
        result = texfmt(src, 'test.tex', config=config)
        assert '\\section{Foo}\\label{sec:foo}' in result.text

    def test_weight_zero_disables_fixable_rule(self):
        src = 'inline \\(x\\) and display \\[ y \\]'
        config = {'threshold': 5, 'weights': {'math_delimiters_display': 0}}
        result = texfmt(src, 'test.tex', config=config)
        assert result.text == 'inline $x$ and display \\[ y \\]'
        assert 'math_delimiters_display' not in [r.id for r, _ in result.clangs]

    def test_display_math_delimiters_default_off_in_texfmt(self):
        src = 'inline \\(x\\) and display \\[ y \\]'
        result = texfmt(src, 'test.tex')
        assert result.text == 'inline $x$ and display \\[ y \\]'

    def test_display_math_delimiters_can_be_enabled(self):
        src = 'display \\[ y \\]'
        config = {'threshold': 5, 'weights': {'math_delimiters_display': 5}}
        result = texfmt(src, 'test.tex', config=config)
        assert result.text == 'display $$ y $$'
        assert 'math_delimiters_display' in [r.id for r, _ in result.clangs]

    def test_equation_math_delimiters_default_off_in_texfmt(self):
        src = '\\[ y \\]'
        result = texfmt(src, 'test.tex')
        assert result.text == src

    def test_equation_math_delimiters_can_be_enabled(self):
        src = '\\[ y \\]'
        config = {
            'threshold': 5,
            'weights': {
                'math_delimiters_equation': 5,
                'equation_punctuation': 0,
            },
        }
        result = texfmt(src, 'test.tex', config=config)
        assert result.text == '\\begin{equation}\ny\n\\end{equation}'
        assert 'math_delimiters_equation' in [r.id for r, _ in result.clangs]

    def test_max_iter_must_be_positive(self):
        with pytest.raises(ValueError, match='max_iter must be >= 1'):
            texfmt('hello', 'test.tex', max_iter=0)

    def test_fixable_rules_sweep_to_fixed_point(self):
        def a_to_b(text):
            return text.replace('A', 'B')

        def b_to_c(text):
            return text.replace('B', 'C')

        fake_a = Rule(98, 'test_a_to_b', 'A to B', a_to_b, 5, True, 100)
        fake_b = Rule(99, 'test_b_to_c', 'B to C', b_to_c, 5, True, 10)
        RULES.extend([fake_a, fake_b])
        try:
            result = texfmt('A', 'test.tex', max_iter=3)
        finally:
            RULES.remove(fake_a)
            RULES.remove(fake_b)

        assert result.text == 'C'
        assert result.converged is True
        assert result.iterations == 3
        assert not any(item[0].id == 'max_iter' for item in result.clunks)
        assert [r.id for r, _ in result.clangs][-2:] == ['test_b_to_c', 'test_a_to_b']

    def test_max_iter_exhaustion_reports_clunk(self):
        def a_to_b(text):
            return text.replace('A', 'B')

        def b_to_c(text):
            return text.replace('B', 'C')

        fake_a = Rule(98, 'test_a_to_b', 'A to B', a_to_b, 5, True, 100)
        fake_b = Rule(99, 'test_b_to_c', 'B to C', b_to_c, 5, True, 10)
        RULES.extend([fake_a, fake_b])
        try:
            result = texfmt('A', 'test.tex', max_iter=2)
        finally:
            RULES.remove(fake_a)
            RULES.remove(fake_b)

        assert result.text == 'C'
        assert result.converged is False
        assert result.iterations == 2
        assert any(item[0].id == 'max_iter' for item in result.clunks)

    def test_max_iter_one_preserves_single_pass_behaviour(self):
        def a_to_b(text):
            return text.replace('A', 'B')

        def b_to_c(text):
            return text.replace('B', 'C')

        fake_a = Rule(98, 'test_a_to_b', 'A to B', a_to_b, 5, True, 100)
        fake_b = Rule(99, 'test_b_to_c', 'B to C', b_to_c, 5, True, 10)
        RULES.extend([fake_a, fake_b])
        try:
            result = texfmt('A', 'test.tex', max_iter=1)
        finally:
            RULES.remove(fake_a)
            RULES.remove(fake_b)

        assert result.text == 'B'
        assert result.converged is False
        assert not any(item[0].id == 'max_iter' for item in result.clunks)

    def test_result_type(self):
        result = texfmt('hello', 'test.tex')
        assert isinstance(result, ClatResult)
