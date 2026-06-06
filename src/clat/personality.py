"""
clat personality — quirky messages for a tool with opinions.

Each category is a list; the CLI picks one at random per invocation.

Three categories of issue:
  clang — auto-fixed (weight >= threshold, fixable)
  clunk — needs manual attention (weight >= threshold, NOT fixable)
  splat — advisory (0 < weight < threshold)
"""

import random

GREETINGS = [
    "Perchance, your LaTeX needs tidying.",
    "Lo! Let us inspect this manuscript.",
    "Forsooth, another .tex file approaches.",
    "Hark! The source code beckons.",
    "Pray tell, what horrors lurk within?",
    "Right then, let's have a look.",
    "Once more unto the .tex, dear friends.",
    "Methinks this document needs attention.",
    "Behold! A manuscript in need of polish.",
    "What fresh dollary is this?",
    "Another day, another dangling dollar sign.",
    "Let us see what the cat dragged in.",
]

CLEAN = [
    "Clean as a whistle. Moot point, really.",
    "Spotless. Nothing to see here.",
    "Immaculate. You may proceed.",
    "Not a blemish. Perchance you've run clat before?",
    "Pristine. The rare specimen.",
    "Nary a clang, clunk, nor splat. Bravo.",
    "Impeccable. One might say... moot.",
    "Flawless. Lo, a unicorn!",
]

FIXED = [
    "{n} {noun} tidied. You're welcome.",
    "{n} {noun} dispatched with aplomb.",
    "{n} {noun} corrected. The manuscript breathes easier.",
    "{n} {noun} vanquished. Huzzah!",
    "{n} {noun} mended. Perchance it was always thus.",
    "Lo, {n} {noun} set right.",
    "{n} {noun} remedied. The LaTeX gods are appeased.",
    "{n} {noun} fixed. Moot henceforth.",
]

CLANG_INTROS = [
    "CLANG",
    "Fixed",
    "Sorted",
    "Done",
    "Mended",
]

CLUNK_INTROS = [
    "CLUNK",
    "Oi",
    "Ahem",
    "Obstinate",
    "Immovable",
    "Stuck",
    "Unmendable",
    "Stubborn",
]

SPLAT_INTROS = [
    "SPLAT",
    "Alas",
    "Egads",
    "Tsk",
    "Hmm",
    "Oof",
    "Crikey",
    "Blimey",
    "Zounds",
]

CHECK_DIRTY = [
    "{n} {noun} found. This will not do.",
    "{n} {noun} lurking. Run clat to fix.",
    "Lo, {n} {noun}. The manuscript protests.",
    "{n} {noun} detected. Perchance run clat?",
    "{n} {noun}. Moot if you fix them now.",
]

GOODBYES = [
    "Fare thee well.",
    "Until next time.",
    "Go forth and compile.",
    "May your builds be clean.",
    "Adieu.",
    "The manuscript is in your hands now.",
    "pdflatex awaits.",
    "Toodle-pip.",
    "Cheerio.",
]


def pick(messages, **kwargs):
    """Pick a random message and format it."""
    return random.choice(messages).format(**kwargs)


def clang_or_clangs(n):
    return "clang" if n == 1 else "clangs"


def clunk_or_clunks(n):
    return "clunk" if n == 1 else "clunks"


def splat_or_splats(n):
    return "splat" if n == 1 else "splats"


def fix_or_fixes(n):
    return "fix" if n == 1 else "fixes"
