"""clat — Colin's LaTeX Tidy. Somewhere between a clang and a splat."""

__version__ = '0.9.0'

from .rules import (
    texfmt, load_config, save_config, generate_default_config,
    ClatResult, Rule, RULES, DEFAULT_THRESHOLD,
)

__all__ = [
    'texfmt', 'load_config', 'save_config', 'generate_default_config',
    'ClatResult', 'Rule', 'RULES', 'DEFAULT_THRESHOLD', '__version__',
]
