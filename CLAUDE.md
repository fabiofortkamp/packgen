# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture

`packgen` is a thin Python wrapper that drives a Blender-based physics simulation to generate particle packings (the primary output is an STL mesh of the settled particles).

Two-process architecture:

- `src/packgen/__init__.py` — the installed `packgen` console script. Its `main()` only locates the Blender executable (platform-specific in `find_Blender_executable()`) and `subprocess.run`s Blender with `-P src/packgen/blend.py`, forwarding everything after `--` on the CLI to the Blender process. The host Python interpreter does almost no work.
- `src/packgen/blend.py` — runs **inside Blender's embedded Python** (the `bpy` module is only available there). It reads a JSON parameter file (default `parameters.json` in cwd, or the path after `--`), builds the container + prismatic particles, runs the rigid-body simulation, and writes `packing_<basename>.{blend,stl,json}` to cwd. Each output file is gated by `save_blender_file` / `save_stl_file` / `save_json_file` in the input. The output JSON echoes inputs but with the actually-used `seed` (input `seed: null` ⇒ random seed generated and persisted).

Particles are regular prisms ("A" and "B" types) parameterized by circumscribed radius, thickness, density, and mass fraction. See `examples/parameters.json` for the canonical input schema; `config_example.json` in `src/packgen/` is a legacy/alternative schema and not what `blend.py` currently consumes.

Because the simulation runs under Blender's interpreter, `blend.py` cannot be imported and exercised end-to-end from the dev venv — only its pure helpers (e.g. `volume_prism`) are unit-testable. Keep new geometry/math helpers as plain functions at module scope so tests can import them via `from packgen import blend` without triggering `bpy`-dependent code paths at import time.

## Common commands

This project uses `uv` and targets Python 3.11 (see `.python-version`, `pyproject.toml`).

```shell
# install dev environment
uv sync

# run the full test suite
uv run pytest

# run a single test
uv run pytest test/test_volumes.py::test_volume_prism_coincides_with_hexagon

# lint (ruff config lives in pyproject.toml — extends ANN, FBT, B, A, C, D)
uv run ruff check .

# type check
uv run basedpyright

# run the actual tool (requires Blender installed and on PATH as `Blender`/`blender`)
uv run packgen -- examples/parameters.json
```

Note: `uv run pytest` only exercises the pure-Python helpers. There is no automated test for the Blender pipeline; verify changes to `blend.py` by running `packgen` against an example parameters file and inspecting the produced `.stl`/`.blend`.

## Interaction Rules

* Ask clarifying questions if input is unclear.
* Explain why and suggest alternatives if task is not feasible.
* Use structured, readable formatting (headings, lists, code blocks).
* Follow instructions closely and explain clearly what you have done.
* Don't modify code unrelated to the current task.
* Try always to match the style of the code you are touching.

## Coding Standards

* Write meaningful tests with assertions for all code.
* Avoid duplicated test assertions.
* Maintain evolving test coverage.
* Apply Four Rules of Simple Design:
	1. Code works (passes tests).
	2. Reveals intent.
	3. No duplication.
	4. Minimal elements.

* Prefer functional style:

	* Use explicit parameters.
	* Prefer immutability.
	* Prefer declarative over imperative.
	* Minimize state.

## Workflow

* Read `spec.md` before coding.
* Update `spec.md` after task (log changes).
* Write and pass tests before finalizing.
* Keep a `README.md` with setup/run info.
* Store all docs/specs in Markdown.

## Commit Strategy

* One prompt = one commit.
* Each commit:
	* Self-contained.
	* Includes tests.
	* Uses 50/70 commit message format.

## Safe Practices

* Do not change test assertions during refactoring.
* Do not skip failing tests.
* Do not invent unknown APIs; ask if you are unsure.
