"""Run packing simulation in Blender.

This script reads parameters from a file passed on the
command line, or "parameters.json" by default, and
simulates particles falling due to the gravitational field
inside a container box.

There are two types of particles, "A" and "B". The particles are assumed to be
prismatic, with the polygonal faces characterized by a circumscribed radius,
and the prism having a given height. The parameters file describes these
geometric parameters, together with the densities of the particles.
The container configuration is also included.

Original design and implementation by Andrea Insinga.
"""

import json
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import bpy as _bpy

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from packgen.core import (
    PARTICLE_COLOR,
    ContainerSpec,
    PackingSpec,
    Parameters,
    ParticleSpec,
    ParticleType,
    PistonSpec,
    build_packing_spec,
)

bpy: Any = _bpy


def get_parameters_file() -> str:
    """Parse argument lists and return parameters file name."""
    if "--" in sys.argv:
        argv = sys.argv[sys.argv.index("--") + 1 :]  # get all args after "--"
        parameters_file = argv[0]
    else:
        parameters_file = "parameters.json"
    return parameters_file


def _make_particle_material(particle_type: ParticleType) -> Any:
    r, g, b = PARTICLE_COLOR[particle_type]
    mat = bpy.data.materials.new("GenericMaterial")
    mat.diffuse_color = (r, g, b, 1.0)
    mat.specular_intensity = 0
    return mat


class Particle:
    """Create one Blender particle from a pure particle specification."""

    def __init__(self, spec: ParticleSpec, *, num_sides: int) -> None:
        """Create the mesh, rigid body, and material for one particle."""
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=num_sides,
            radius=spec.radius,
            depth=spec.height,
            enter_editmode=False,
            location=spec.location,
        )
        obj = bpy.context.active_object
        obj.rotation_euler = spec.rotation
        bpy.ops.rigidbody.object_add(type="ACTIVE")
        obj.rigid_body.friction = spec.friction
        obj.rigid_body.restitution = spec.restitution
        obj.rigid_body.mass = spec.mass
        obj.rigid_body.linear_damping = spec.damping
        obj.active_material = _make_particle_material(spec.particle_type)


class Container:
    """Create the Blender container from a pure container specification."""

    def __init__(self, spec: ContainerSpec) -> None:
        """Create an open cube-like container."""
        height_to_side_scale = spec.height / spec.side_length
        bpy.ops.mesh.primitive_cube_add(
            size=spec.side_length,
            enter_editmode=False,
            location=(0, 0, spec.height / 2),
            scale=(1, 1, height_to_side_scale),
        )
        cube = bpy.context.active_object

        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.mesh.select_mode(type="FACE")

        bpy.ops.object.mode_set(mode="OBJECT")
        top_face = [face for face in cube.data.polygons if face.normal.z > 0.9]
        for face in top_face:
            face.select = True

        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.delete(type="FACE")
        bpy.ops.object.mode_set(mode="OBJECT")

        modifier = cube.modifiers.new(name="Solidify", type="SOLIDIFY")
        modifier.thickness = spec.wall_thickness

        bpy.ops.rigidbody.object_add(type="PASSIVE")
        cube.rigid_body.collision_shape = "MESH"
        cube.name = "Container"
        self.name = cube.name


class Piston:
    """Create the optional Blender piston from a pure piston specification."""

    def __init__(self, spec: PistonSpec) -> None:
        """Create the piston mesh and rigid body when enabled."""
        self.name: str | None = None

        if spec.enabled:
            bpy.ops.mesh.primitive_cube_add(
                size=spec.side_length,
                enter_editmode=False,
                align="WORLD",
                location=(0, 0, spec.z),
                scale=(1, 1, 1),
            )

            piston = bpy.context.active_object
            bpy.ops.rigidbody.object_add(type="ACTIVE")
            piston.rigid_body.friction = 0
            piston.rigid_body.restitution = 0
            piston.rigid_body.mass = spec.mass
            piston.name = "Piston"
            self.name = piston.name


class PackingSimulation:
    """Packing simulation to be performed with the physics-engine."""

    def __init__(self, spec: PackingSpec, *, suffix: str) -> None:
        """Prepare a Blender simulation from a pure packing specification."""
        self.spec = spec
        self._suffix = suffix
        self._clean_state()

    def run(self) -> None:
        """Run the particle packing simulation."""
        self._initialize_particles()

        piston = self._initialize_piston()
        container = self._initialize_container()

        self.bake_and_export(objects_to_delete=[container, piston])

    def _initialize_piston(self) -> Piston:
        return Piston(self.spec.piston)

    def _initialize_container(self) -> Container:
        return Container(self.spec.container)

    def _initialize_particles(self) -> None:
        for particle in self.spec.particles:
            Particle(particle, num_sides=self.spec.parameters.num_sides)

    @staticmethod
    def _clean_state() -> None:
        bpy.ops.object.select_all(action="DESELECT")
        bpy.ops.object.select_by_type(type="MESH")
        bpy.ops.object.delete()

        bpy.ops.ptcache.free_bake_all()

    def bake_and_export(
        self,
        objects_to_delete: Any = None,
    ) -> None:
        """Bake the physics simulation and export the results."""
        scene = bpy.context.scene
        scene.frame_start = self.spec.frame_start
        scene.frame_end = self.spec.frame_end
        scene.rigidbody_world.point_cache.frame_start = scene.frame_start
        scene.rigidbody_world.point_cache.frame_end = scene.frame_end

        parameters = self.spec.parameters
        scene.gravity = self.spec.gravity

        bpy.ops.ptcache.bake_all()

        scene.frame_set(self.spec.frame_end)

        output_dir = Path(os.getcwd())
        suffix = self._suffix
        if parameters.save_blender_file:
            blend_path = output_dir / f"packing_{suffix}.blend"
            bpy.ops.wm.save_mainfile(filepath=str(blend_path))
        if parameters.save_json_file:
            json_path = output_dir / f"packing_{suffix}.json"

            with open(json_path, mode="w") as f:
                json.dump(asdict(parameters), f)

        for object_to_delete in objects_to_delete or []:
            if object_to_delete and object_to_delete.name in bpy.data.objects:
                obj = bpy.data.objects[object_to_delete.name]
                bpy.data.objects.remove(obj, do_unlink=True)

        if parameters.save_stl_file:
            stl_path = output_dir / f"packing_{suffix}.stl"
            bpy.ops.wm.stl_export(filepath=str(stl_path))

        if parameters.quit_on_finish:
            bpy.ops.wm.quit_blender()


def main() -> None:
    """Load parameters and run the packing simulation."""
    parameters_file = get_parameters_file()
    parameters = Parameters.from_json(parameters_file)
    suffix = Path(parameters_file).stem
    PackingSimulation(build_packing_spec(parameters), suffix=suffix).run()


if __name__ == "__main__":
    main()
