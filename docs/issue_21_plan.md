# Issue 21 Implementation Notes

Issue: https://github.com/cmt-dtu-energy/packgen/issues/21

## Testing seam

The testable core lives in `packgen.core`. It contains the JSON-backed
`Parameters` model, geometry/mass calculations, particle type selection, and
`build_packing_spec()`, which returns a pure `PackingSpec` for the Blender
adapter to execute.

The Blender adapter lives in `packgen.blend`. It imports `bpy`, consumes
`PackingSpec`, creates meshes/materials/rigid bodies, bakes the simulation, and
exports `.blend`, `.stl`, and `.json` outputs.

## Covered by unit tests

- Parameter loading, defaults, unknown-key failures, and missing-key failures.
- Prism volume, particle dimensions, density, and mass calculations.
- B-particle count calculation from target B mass fraction.
- Deterministic particle specification generation for a fixed seed.
- Particle grid coordinates, piston dimensions, container dimensions, frame
  range, and gravity in `PackingSpec`.
- Host-Python launcher behavior in `packgen.__init__`, including platform-based
  Blender executable selection and `subprocess.run()` arguments.

## Not covered by default unit tests

The default suite does not execute the Blender adapter's `bpy` calls. Those
paths require Blender's runtime and are better treated as integration behavior:

- Mesh, material, and rigid-body creation.
- Physics cache baking.
- Deleting Blender scene objects.
- `.blend` and `.stl` export operators.
- Quitting Blender after the run.

## Verified Blender version

Local verification command:

```shell
/Applications/Blender.app/Contents/MacOS/Blender --version
```

Verified locally with Blender 5.0.1 on Darwin. The package metadata currently
depends on `bpy>=4.4.0`, so release documentation should distinguish the minimum
declared dependency from the Blender application version actually smoke-tested.
