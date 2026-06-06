# CLI reference

The `clat` command has three forms: the default **format** command, plus the
`list` and `set` subcommands.

```text
clat <files...>              Format .tex files in place
clat --check <files...>      Dry run: report issues without fixing
clat -o out.tex in.tex       Write to a different file
clat --threshold N <files>   Override threshold for this run

clat list                    List all rules with weights and categories
clat list --config path      Use a specific config file

clat set <rule#> <weight>    Set a rule weight in .clat.toml
clat set --threshold N       Set the threshold in .clat.toml
clat set --init              Create .clat.toml with defaults
clat set --reset             Restore .clat.toml to defaults
clat set --config path       Target a specific config file

clat --version               Show version
```

---

## `clat` — format

```text
clat [options] <files...>
```

Apply the configured rules to one or more `.tex` files. By default files are
rewritten **in place**; a file is only touched if something actually changes.

| Option | Description |
|--------|-------------|
| `files...`            | One or more `.tex` files to format. |
| `-o`, `--output PATH` | Write output to `PATH` instead of editing in place. Single input only. |
| `--check`             | Dry run — report what would change without modifying any file. |
| `--config PATH`       | Read configuration from `PATH` instead of the default search locations. |
| `--threshold N`       | Override the threshold for this run only (does not edit the config). |
| `--version`           | Print the clat version and exit. |

**Examples**

```bash
clat main.tex                      # format in place
clat main.tex appendix.tex         # format several files
clat --check main.tex              # dry run
clat -o clean.tex main.tex         # write elsewhere, leave the input alone
clat --threshold 3 main.tex        # one-off stricter run
```

**Exit status**

| Code | Meaning |
|------|---------|
| `0`  | Clean — nothing to fix or flag. |
| `1`  | Issues found: a missing file, or any remaining clunks/splats (and, under `--check`, any pending fixes). |

The non-zero exit on outstanding issues makes `clat --check` suitable for CI
and pre-commit hooks.

---

## `clat list`

```text
clat list [--config PATH]
```

List every rule with its number, effective weight, and the category it falls
into for the current threshold. A `✓` marks a fixable rule, `✗` a detect-only
one.

| Option | Description |
|--------|-------------|
| `--config PATH` | Read configuration from `PATH`. |

---

## `clat set`

```text
clat set [<rule#> <weight>] [--threshold N] [--init] [--reset] [--config PATH]
```

Edit the configuration file (default `./.clat.toml`).

| Option | Description |
|--------|-------------|
| `<rule#> <weight>` | Set the weight (1–10) of the rule with the given number. |
| `--threshold N`    | Set the threshold (1–10). |
| `--init`           | Create `.clat.toml` with defaults. Refuses to overwrite an existing file. |
| `--reset`          | Overwrite `.clat.toml` with defaults. |
| `--config PATH`    | Operate on `PATH` instead of `./.clat.toml`. |

**Examples**

```bash
clat set --init              # create .clat.toml
clat set --threshold 7       # raise the threshold
clat set 12 9                # set rule 12 (ellipsis) to weight 9
clat set --reset             # restore defaults
```

Running `clat set` with no actionable arguments prints help and exits `1`.
