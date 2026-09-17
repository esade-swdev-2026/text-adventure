# app

> **First thing: rename `app` to your project.** It appears in this file, in
> `pyproject.toml` (`name`, `[project.scripts]`, `[tool.hatch.build.targets.wheel]`),
> in the folder `src/app/`, and in the imports under `tests/`. Session 5's lab walks
> you through it.

One or two sentences on what your program does and who it is for.

## Install

```
uv sync
```

This creates a virtual environment and installs everything, including the development
tools, from `uv.lock` — the committed file that pins exact versions so every teammate
and CI resolve the same ones. When you change a dependency in `pyproject.toml`, run
`uv lock` and commit the updated `uv.lock`; CI fails if the two disagree.

## Run

```
uv run app --help
uv run app greet World
uv run app greet World --count 3
```

## Develop

```
uv run ruff check .          # lint
uv run ruff format .         # format (CI runs `--check` and fails on a diff)
uv run mypy src tests        # types
uv run pytest                # tests
```

These four commands are exactly what `.github/workflows/check.yml` runs on every push.
If they pass here, CI passes.

## Layout

```
src/app/          your package — importable, installable, not just a script
  cli.py          the typer command-line interface
  __main__.py     lets `python -m app` work
tests/            pytest tests, mirroring src/
pyproject.toml    dependencies and tool configuration — the single source of truth
```
