# CLI reference

The `clat` command has three forms: the default **format** command, plus the
`list` and `set` subcommands.

```text
clat <files...>              Format .tex files in place
clat -r <root.tex...>        Recursively format LaTeX inputs/includes
clat --recursive <root.tex>  Long form of -r
clat --check <files...>      Dry run: report issues without fixing
clat --check -r <root.tex>   Dry run a multi-file document
clat -o out.tex in.tex       Write to a different file
clat --threshold N <files>   Override threshold for this run
clat --max-iter N <files>    Maximum fixable-rule sweeps (default 5)

clat list                    List all rules with weights and categories
clat list --config path      Use a specific config file

clat set <rule-id|rule#> <weight>
                                Set a rule weight in .clat.toml
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
Fixable rules are swept to a text fixed point by default (up to 5 sweeps), then
detect-only rules run once on the final text.

| Option | Description |
|--------|-------------|
| `files...`            | One or more `.tex` files to format. |
| `-r`, `--recursive`   | Follow `\input`/`\include`-style commands and also format every `.tex` file they pull in. See [Multi-file documents](multi-file.md). Cannot be combined with `-o`. |
| `-o`, `--output PATH` | Write output to `PATH` instead of editing in place. Single input only. |
| `--check`             | Dry run — report what would change without modifying any file. |
| `--config PATH`       | Read configuration from `PATH` instead of the default search locations. |
| `--threshold N`       | Override the threshold for this run only (does not edit the config). |
| `--max-iter N`        | Maximum fixable-rule sweeps before stopping. Default: `5`; use `1` for single-pass behaviour. |
| `--version`           | Print the clat version and exit. |

**Examples**

```bash
clat main.tex                      # format in place
clat main.tex appendix.tex         # format several files
clat -r main.tex                   # follow inputs/includes and format them all
clat --check -r main.tex           # dry run the whole multi-file document
clat --check main.tex              # dry run
clat -o clean.tex main.tex         # write elsewhere, leave the input alone
clat --threshold 3 main.tex        # one-off stricter run
clat --max-iter 1 main.tex         # single-pass run
```

**Exit status**

| Code | Meaning |
|------|---------|
| `0`  | Clean — nothing to fix or flag. |
| `1`  | Issues found: a missing file, any remaining clunks/splats, max-iteration non-convergence, or (under `--check`) any pending fixes. |

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
clat set [<rule-id|rule#> <weight>] [--threshold N] [--init] [--reset] [--config PATH]
```

Edit the configuration file (default `./.clat.toml`).

| Option | Description |
|--------|-------------|
| `<rule-id|rule#> <weight>` | Set the weight (0–10) of a rule; 0 disables it. Prefer ids for scripts. |
| `--threshold N`    | Set the threshold (1–10). |
| `--init`           | Create `.clat.toml` with defaults. Refuses to overwrite an existing file. |
| `--reset`          | Overwrite `.clat.toml` with defaults. |
| `--config PATH`    | Operate on `PATH` instead of `./.clat.toml`. |

**Examples**

```bash
clat set --init              # create .clat.toml
clat set --threshold 7       # raise the threshold
clat set ellipsis 9          # set ellipsis to weight 9
clat set 14 9                # also accepted: current list number for ellipsis
clat set --reset             # restore defaults
```

Running `clat set` with no actionable arguments prints help and exits `1`.
