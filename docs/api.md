# Python API

Beyond the command line, `clat` is a small library. Import it to format LaTeX
source from your own scripts, editors, or build tools.

```python
from clat import texfmt, load_config

config = load_config()                 # nearest .clat.toml, or defaults
result = texfmt(open("main.tex").read(), filename="main.tex", config=config)

print(result.text)                     # the formatted source
for rule, n_hits in result.clangs:     # what was auto-fixed
    print(f"clang: {rule.name} ({n_hits})")
for rule, fname, line, msg in result.clunks:
    print(f"clunk: {fname}:{line}: {msg}")
```

If you omit `config`, `texfmt` uses the built-in defaults (threshold
`#!python 5`, every rule at its default weight). To run with a custom
threshold without a file on disk, build the dict yourself:

```python
config = {"threshold": 8, "weights": {"ellipsis": 9}}
result = texfmt(source, config=config)
```

By default, `texfmt` runs fixable rules to a text fixed point, up to 5 sweeps.
Pass `max_iter=1` for single-pass behaviour:

```python
result = texfmt(source, config=config, max_iter=1)
```

---

## Formatting

::: clat.texfmt

::: clat.ClatResult

---

## Configuration

::: clat.load_config

::: clat.save_config

::: clat.generate_default_config

---

## The rule registry

::: clat.Rule

::: clat.RULES
    options:
      show_if_no_docstring: true

::: clat.DEFAULT_THRESHOLD
    options:
      show_if_no_docstring: true

---

## Multi-file discovery

For multi-file documents, `clat.cli.discover_tex_files` expands a list of root
files into the full, ordered, de-duplicated set of `.tex` files reachable
through `\input`/`\include`-style commands — the same traversal the `-r` flag
uses. See [Multi-file documents](multi-file.md).

```python
from clat.cli import discover_tex_files

for path in discover_tex_files(["main.tex"]):
    print(path)
```

::: clat.cli.discover_tex_files
