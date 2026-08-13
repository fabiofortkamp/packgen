# Issue Attack Plan

Source tracker: https://github.com/cmt-dtu-energy/packgen/issues

`origin` has issues disabled, so the actionable issues are in the upstream
repository. The open issue set is release-readiness work: testability, CI,
packaging metadata, documentation, worked examples, release archival, and
distribution.

## Recommended Order

1. #21 Refactor Blender boundary and raise core coverage to >=80%

   Do this first. The current architecture mixes pure config/math logic with
   `bpy` calls in `src/packgen/blend.py`, which makes most behavior difficult
   to test outside Blender's embedded Python. Split pure logic into normal
   Python modules, keep the Blender adapter thin, and document what remains
   untested and why.

   Target outcome: core non-`bpy` modules have >=80% coverage, the Blender
   boundary is explicit, and verified Blender versions are documented.

2. #22 Set up GitHub Actions CI + coverage badges

   Do this after #21 so CI measures the intended test boundary. Add a workflow
   for push and pull requests, run the supported Python version matrix, report
   coverage, and add CI/coverage badges to the README.

3. #26 Finalize packaging metadata, LICENSE, CITATION.cff

   This is the release foundation. `pyproject.toml` already has basic metadata,
   but it needs a release pass for dependency/version policy, licensing
   correctness, and citation metadata. Add `CITATION.cff`.

4. #23 Write README: install, quickstart, Blender setup, scope, maintainer note

   Update this after #21 and #26 so the README reflects the actual architecture,
   supported Blender version, install path, and tested limitations. The rendered
   GIF from #25 can be added in a follow-up patch if the worked example is not
   ready yet.

5. #24 Publish docs site with mkdocs-material + mkdocstrings

   Do this after the module layout stabilizes from #21. Set up the docs site,
   generate API reference from docstrings, publish through GitHub Pages, and
   link it from the README.

6. #25 Add worked example producing the packing animation

   Produce a reproducible script or notebook that runs the example end to end,
   render the animation to a GIF, and embed it in the README/docs. This can be
   done after basic docs are in place, or in parallel if Blender rendering is
   the bottleneck.

7. #27 Tag v1.0.0 release with Zenodo archival DOI

   This explicitly depends on #26. It should also wait for #21, #22, and #23 at
   minimum so the v1.0.0 tag has testable core behavior, CI, and usable install
   documentation. Enable Zenodo, tag `v1.0.0`, confirm the DOI, and add it to
   README/CITATION.

8. #28 Decide and handle distribution: PyPI vs git-install docs

   This comes last because it depends on #27 and requires an external DTU
   decision. If DTU wants ongoing PyPI maintenance, publish to PyPI. Otherwise,
   document tagged git installation in the README.

## Milestones

### 1. Make it trustworthy

- #21 Refactor Blender boundary and raise core coverage to >=80%
- #22 Set up GitHub Actions CI + coverage badges

### 2. Make it releasable

- #26 Finalize packaging metadata, LICENSE, CITATION.cff
- #23 Write README: install, quickstart, Blender setup, scope, maintainer note
- #24 Publish docs site with mkdocs-material + mkdocstrings
- #25 Add worked example producing the packing animation

### 3. Release and distribute

- #27 Tag v1.0.0 release with Zenodo archival DOI
- #28 Decide and handle distribution: PyPI vs git-install docs

## Current Baseline

- Local branch: `develop`
- Working tree at inspection time: clean
- Tests: `uv run pytest` -> 21 passed
- Coverage: `uv run python -m coverage report` -> 46% total
- Main misses: Blender-dependent paths in `blend.py` and subprocess launch logic
  in `src/packgen/__init__.py`

