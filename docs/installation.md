# Installation

## From PyPI

```bash
pip install clat-tidy
```

This installs the `clat` command on your `PATH`.

!!! info "Distribution name vs command name"
    You install **`clat-tidy`** but run **`clat`**. The PyPI distribution is
    called `clat-tidy` because the name `clat` was already taken; the command,
    the importable package, and the config files are all still `clat`.

Requires **Python ≥ 3.8**. On Python < 3.11, the [`tomli`][tomli] TOML reader
is installed automatically (3.11+ uses the standard-library `tomllib`).

`clat`'s only runtime dependency is [`rich`][rich], for its coloured terminal
output.

[tomli]: https://pypi.org/project/tomli/
[rich]: https://pypi.org/project/rich/

## Verify

```bash
clat --version
```

```text
clat 0.5.0
```

## With pipx

To keep `clat` isolated from your project environments:

```bash
pipx install clat-tidy
```

## Development install

Clone the repository and install in editable mode:

```bash
git clone https://github.com/ccaprani/clat.git
cd clat
pip install -e .
```

To build the documentation as well, install the `docs` extra:

```bash
pip install -e '.[docs]'
mkdocs serve   # live preview at http://127.0.0.1:8000
```

Run the test suite with:

```bash
python -m pytest tests/ -v
```
