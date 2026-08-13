# Plan: Multi-Version Blender Testing

Follow-on to [issue 21](https://github.com/cmt-dtu-energy/packgen/issues/21), which asked
that the verified Blender versions be documented. Documenting one version is a stopgap;
this plan makes "which versions work" a question the test suite answers.

## Strategy: test against `bpy` wheels, not Blender app installs

The `bpy` package on PyPI is Blender compiled as an importable Python module. It is already
a declared dependency (`pyproject.toml`), and it is already installed in the dev venv, so a
version matrix costs one virtualenv per version — no `.dmg` downloads, no
`/Applications/Blender-<version>.app` juggling, and the same commands work unchanged on a
Linux CI runner.

### Version / interpreter constraint

`bpy` wheels are built against one specific CPython version. This determines the reachable
matrix:

| bpy versions                                        | Python | Reachable today |
| --------------------------------------------------- | ------ | --------------- |
| 4.2.x, 4.3.0, 4.4.0, 4.5.x (LTS), 5.0.0, 5.0.1        | cp311  | yes — matches the current `requires-python = ">=3.11, <3.12"` |
| 5.1.x, 5.2.0                                          | cp313  | no — blocked by the pin |

Roughly 24 builds spanning 4.2 through 5.0.1 are testable on the interpreter already
targeted. Blender 5.1 is where the cp313 break lands; supporting it means widening
`requires-python` and running a second interpreter in the matrix. Plan for that, but it is
not a prerequisite for anything below.

### Verified feasibility

Confirmed on 2026-08-13 (macOS, Darwin 25.5.0):

- `import bpy` in the existing dev venv yields Blender 4.4.0 under Python 3.11.12.
- A clean `uv venv --python 3.11` with `bpy==4.5.12` installs and runs alongside it.
- `packgen.blend.main()` executes **in-process** under both, with no Blender application
  and no subprocess.

That last point contradicts a claim in `CLAUDE.md`:

> Because the simulation runs under Blender's interpreter, `blend.py` cannot be imported
> and exercised end-to-end from the dev venv — only its pure helpers are unit-testable.

This is no longer true and should be corrected, because it is the assumption that kept the
`bpy` adapter untested. The adapter can be exercised directly with real assertions.

## Bug found while validating this plan

**With `use_piston: false`, every run crashes before the STL is written.** Reproduced
identically on bpy 4.4.0, bpy 4.5.12, and the Blender 5.0.1 application:

```
TypeError: bpy_prop_collection.__contains__: expected a string or a tuple of strings
```

Root cause: `Piston.name` is `None` when the piston is disabled (`src/packgen/blend.py:124`),
but the cleanup loop guards the wrapper object rather than the name
(`src/packgen/blend.py:210`):

```python
if object_to_delete and object_to_delete.name in bpy.data.objects:
```

The `Piston` instance is always truthy, so `None in bpy.data.objects` raises. STL export
happens *after* this loop (`src/packgen/blend.py:214`), so the primary output is never
produced.

This is pre-existing, not a regression from the `core`/`blend` split: at `b5f071e` the old
`Piston` never assigned `self.name` at all, raising `AttributeError` at the same line. Both
files in `examples/` set `use_piston: true`, which is why it went unnoticed.

### Why the current smoke test misses it

`test/test_blender_smoke.py` asserts `returncode == 0` and that the output JSON exists. Both
hold while the script is crashing:

- `blender -P script.py` exits **0 even when the script raises an uncaught exception** —
  confirmed by observing the traceback and exit code 0 in the same run.
- The JSON is written at `src/packgen/blend.py:203-207`, before the crash at line 210.

The test is therefore passing vacuously, and it is configured with `use_piston: False` —
the exact broken path. Exit code is not a usable signal for Blender subprocess runs.

## Steps

### 1. Fix the piston cleanup guard

Guard on the name, not the wrapper, in `bake_and_export`:

```python
if object_to_delete is not None and object_to_delete.name is not None:
```

Add a regression test asserting that a `use_piston: false` run reaches STL export. With
in-process `bpy` this needs no subprocess.

### 2. Strengthen the smoke test assertions

Replace the `returncode == 0` check with assertions on the artifacts that matter:

- the `.stl` exists and is non-empty / parses as a mesh with the expected object count;
- stderr contains no `Traceback`.

Add a second parameter set covering `use_piston: false`, so both branches are exercised.

### 3. Add the version matrix runner

A script (`scripts/test_blender_matrix.sh` or a `noxfile.py`) that iterates a pinned list of
`bpy` versions:

```shell
for v in 4.2.23 4.3.0 4.4.0 4.5.12 5.0.1
    uv venv --python 3.11 .venvs/bpy-$v
    VIRTUAL_ENV=.venvs/bpy-$v uv pip install "bpy==$v" "numpy<2" -e .
    ./.venvs/bpy-$v/bin/python -m pytest test/ -m blender
end
```

Design notes:

- Keep the version list explicit and pinned, not "latest" — the point is a reproducible
  statement about which versions were verified.
- Cache `.venvs/` (gitignored); each `bpy` wheel is large, so reinstalling per run is slow.
- Mark these tests `blender` + `slow` so the default `uv run pytest` loop stays fast.
- Have the runner emit a pass/fail table, and generate the README's verified-version list
  from it rather than maintaining that by hand.

### 4. Lift to CI

Linux runners take the same `uv pip install bpy==X`, so the local script ports directly.
Use a GitHub Actions matrix over the pinned version list, with the wheel cache keyed on
version. Run it on a schedule or on release rather than per-push, given wheel size and
runtime.

### 5. Follow-ups

- Correct the `CLAUDE.md` claim about `blend.py` being unimportable from the dev venv.
- Reconcile the dependency floor with reality: `bpy>=4.4.0` is declared, but the only
  version verified end to end so far is the 5.0.1 application. The matrix should either
  justify the floor or raise it.
- Once the adapter is exercised in-process, revisit the `omit` of `src/packgen/blend.py`
  in `[tool.coverage.run]` — some of it becomes legitimately measurable.
- Decide whether to widen `requires-python` to reach bpy 5.1+ (cp313).
