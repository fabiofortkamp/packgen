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

import array as arr
import json
import math
import os
import random
import sys
from dataclasses import asdict, dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any

import bpy


def get_parameters_file() -> str:
    """Parse argument lists and return parameters file name."""
    if "--" in sys.argv:
        argv = sys.argv[sys.argv.index("--") + 1 :]  # get all args after "--"
        parameters_file = argv[0]
    else:
        parameters_file = "parameters.json"
    return parameters_file


@dataclass(frozen=True)
class Parameters:
    """Typed view of the packing-simulation input JSON.

    Field names mirror the JSON keys so the file format is unchanged.
    """

    scale: float
    r_A: float
    r_B: float
    thickness_A: float
    thickness_B: float
    density_A: float
    density_B: float
    num_sides: int
    num_particles_x: int
    num_particles_y: int
    num_particles_z: int
    distance: float
    mass_fraction_B: float
    particle_friction: float
    particle_restitution: float
    particle_damping: float
    mass_piston: float
    end_frame: int
    use_piston: bool
    seed: float
    container_wall_thickness: float = -0.2
    container_piston_slack: float = 0.0
    gravity_field: tuple[float, float, float] = (0.0, 0.0, -9.8)
    save_blender_file: bool = True
    save_json_file: bool = True
    save_stl_file: bool = True
    quit_on_finish: bool = False

    @classmethod
    def from_json(cls, path: str | Path) -> "Parameters":
        """Load parameters from a JSON file.

        A ``seed`` of ``null`` is replaced with a freshly generated random
        value so the actually-used seed can be persisted on output.
        """
        with open(path) as f:
            raw = json.load(f)
        if raw.get("seed") is None:
            raw["seed"] = random.random() * 1e6
        if "gravity_field" in raw:
            raw["gravity_field"] = tuple(raw["gravity_field"])
        return cls(**raw)

    @property
    def num_particles_total(self) -> int:
        """Total number of particles in the initial grid."""
        return self.num_particles_x * self.num_particles_y * self.num_particles_z


def volume_prism(sides: float, radius: float, height: float) -> float:
    """Return the volume of a prism with given number of sides, radius, and height.

    References:
        https://en.wikipedia.org/wiki/Regular_polygon

    """
    return 1 / 2 * sides * radius * radius * math.sin(2 * math.pi / sides) * height


def num_B_particles(parameters: Parameters, num_particles_total: int) -> int:
    """Return the total number of type-B particles to be generated."""
    V_B = volume_prism(parameters.num_sides, parameters.r_B, parameters.thickness_B)
    V_A = volume_prism(parameters.num_sides, parameters.r_A, parameters.thickness_A)

    beta = parameters.density_B * V_B / (parameters.density_A * V_A)

    x_B = parameters.mass_fraction_B
    alpha = 1 / beta * (x_B / (1 - x_B))

    N_B = alpha / (1 + alpha) * num_particles_total

    return math.ceil(N_B)


class ParticleType(IntEnum):
    INVALID = -1
    A = 0
    B = 1


class Particle:
    def __init__(
        self,
        x: float,
        y: float,
        z: float,
        parameters: Parameters,
        *,
        number_fraction_A: float,
    ) -> None:
        particle_type = self._decide_particle_type(number_fraction_A)
        self.type = particle_type
        density = (
            parameters.density_B if particle_type == ParticleType.B else parameters.density_A
        )

        radii = arr.array("d", [parameters.r_A, parameters.r_B])
        heights = arr.array("d", [parameters.thickness_A, parameters.thickness_B])
        scale = parameters.scale
        particle_volume = volume_prism(
            parameters.num_sides,
            scale * radii[particle_type],
            scale * heights[particle_type],
        )

        bpy.ops.mesh.primitive_cylinder_add(
            vertices=parameters.num_sides,
            radius=scale * radii[particle_type],
            depth=scale * heights[particle_type],
            enter_editmode=False,
            location=(x, y, z),
        )
        # Get the active object (the newly created particle)
        particle = bpy.context.active_object
        # Assign a random rotation to the cube
        particle.rotation_euler = (
            random.uniform(0, 6.283185),
            random.uniform(0, 6.283185),
            random.uniform(0, 6.283185),
        )
        # Add rigid body physics to the particle
        bpy.ops.rigidbody.object_add(type="ACTIVE")
        particle.rigid_body.friction = parameters.particle_friction
        particle.rigid_body.restitution = parameters.particle_restitution
        particle.rigid_body.mass = density * particle_volume
        particle.rigid_body.linear_damping = parameters.particle_damping
        mat = bpy.data.materials.new("GenericMaterial")
        mat.diffuse_color = (
            float(COMBINATION_RED[particle_type]),
            float(COMBINATION_GREEN[particle_type]),
            float(COMBINATION_BLUE[particle_type]),
            1.0,
        )
        mat.specular_intensity = 0
        particle.active_material = mat

    @staticmethod
    def _decide_particle_type(number_fraction_A: float) -> ParticleType:
        """Decide which particle type to generate, given the target fraction of A."""
        rnd = random.uniform(0.0, 1.0)
        if rnd > number_fraction_A:
            # if we are supposed to generate only 20% of A,
            # and we randomly select a number bigger than that,
            # then we must generate the other type
            return ParticleType.B
        return ParticleType.A


class Container:
    def __init__(self, side: float, height: float, *, wall_thickness: float) -> None:
        """Create an open cube-like container of given side length and height.

        Args:
            side (float): The length of the sides of the cube.
            height (float): The height of the container.
            wall_thickness (float): Thickness of the solidify modifier
                applied to the container walls.

        """
        height_to_side_scale = height / side
        bpy.ops.mesh.primitive_cube_add(
            size=side,
            enter_editmode=False,
            location=(0, 0, height / 2),
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

        modifier.thickness = wall_thickness

        bpy.ops.rigidbody.object_add(type="PASSIVE")
        cube.rigid_body.collision_shape = "MESH"
        cube.name = "Container"
        self.name = cube.name


class Piston:
    def __init__(
        self, L_container: float, max_z_particles: float, parameters: Parameters
    ) -> None:
        slack = parameters.container_piston_slack
        L_piston = (1 - slack) * L_container
        z_piston = 1.1 * max_z_particles + L_piston / 2

        if parameters.use_piston:
            bpy.ops.mesh.primitive_cube_add(
                size=L_piston,
                enter_editmode=False,
                align="WORLD",
                location=(0, 0, z_piston),
                scale=(1, 1, 1),
            )

            piston = bpy.context.active_object
            bpy.ops.rigidbody.object_add(type="ACTIVE")
            piston.rigid_body.friction = (
                0  # piston does not lose velocity when colliding
            )
            piston.rigid_body.restitution = 0  # piston does not bounce when colliding
            piston.rigid_body.mass = parameters.mass_piston
            piston.name = "Piston"
            self.name = piston.name

        self.z = z_piston
        self.L = L_piston


COMBINATION_RED = arr.array("d", [0.1, 0.8])
COMBINATION_GREEN = arr.array("d", [0.8, 0.4])
COMBINATION_BLUE = arr.array("d", [0.7, 0.7])


class PackingSimulation:
    """Packing simulation to be performed with the physics-engine."""

    def __init__(self, parameters: Parameters, *, suffix: str) -> None:
        self.parameters = parameters
        self._suffix = suffix
        n_B = num_B_particles(parameters, parameters.num_particles_total)
        self._number_fraction_A = 1 - n_B / parameters.num_particles_total
        self._clean_state()
        self._initialize_random_state()

    def run(self) -> None:
        """Run the particle packing simulation."""
        self._initialize_particles()

        piston = self._initialize_piston()
        container = self._initialize_container(piston)

        self.bake_and_export(
            end_frame=self.parameters.end_frame,
            objects_to_delete=[container, piston],
        )

    def _initialize_piston(self) -> Piston:
        parameters = self.parameters
        L_container = parameters.num_particles_x * parameters.distance
        z0 = parameters.distance / 2
        max_z_particles = z0 + parameters.num_particles_z * parameters.distance
        return Piston(L_container, max_z_particles, parameters)

    def _initialize_container(self, piston: Piston) -> Container:
        parameters = self.parameters
        Lxy = parameters.num_particles_x * parameters.distance
        Lz = 1.1 * (piston.z + piston.L / 2)
        return Container(Lxy, Lz, wall_thickness=parameters.container_wall_thickness)

    def _initialize_particles(self) -> None:
        parameters = self.parameters
        distance = parameters.distance
        z0 = distance / 2
        for ix in range(parameters.num_particles_x):
            for iy in range(parameters.num_particles_y):
                for iz in range(parameters.num_particles_z):
                    x = (ix - parameters.num_particles_x / 2 + 0.5) * distance
                    y = (iy - parameters.num_particles_y / 2 + 0.5) * distance
                    z = z0 + iz * distance
                    Particle(
                        x, y, z, parameters, number_fraction_A=self._number_fraction_A
                    )

    @staticmethod
    def _clean_state() -> None:
        # Delete all existing mesh objects
        bpy.ops.object.select_all(action="DESELECT")
        bpy.ops.object.select_by_type(type="MESH")
        bpy.ops.object.delete()

        bpy.ops.ptcache.free_bake_all()

    def _initialize_random_state(self) -> None:
        random.seed(self.parameters.seed)

    def bake_and_export(
        self,
        end_frame: int,
        objects_to_delete: Any = None,
    ) -> None:
        """Bake the physics simulation and export the results.

        Args:
            end_frame (int): The last frame to bake the simulation to.
            objects_to_delete: Objects that were created that should now be removed.
                If None, no object will be removed.

        """
        scene = bpy.context.scene
        # set the frame range
        scene.frame_start = 1
        scene.frame_end = end_frame
        # Match the rigid body world's cache frames to scene start and end
        scene.rigidbody_world.point_cache.frame_start = scene.frame_start
        scene.rigidbody_world.point_cache.frame_end = scene.frame_end

        parameters = self.parameters
        scene.gravity = parameters.gravity_field

        bpy.ops.ptcache.bake_all()

        # step to the last frame so all transforms are final
        scene.frame_set(end_frame)

        # Use the current working directory for all output files
        output_dir = Path(os.getcwd())
        suffix = self._suffix
        if parameters.save_blender_file:
            blend_path = output_dir / f"packing_{suffix}.blend"
            bpy.ops.wm.save_mainfile(filepath=str(blend_path))
        if parameters.save_json_file:
            json_path = output_dir / f"packing_{suffix}.json"

            with open(json_path, mode="w") as f:
                json.dump(asdict(parameters), f)

        # the container deletion should occur after the main saving above
        # to be able to inspect the Blender file
        for object_to_delete in objects_to_delete:
            if object_to_delete and object_to_delete.name in bpy.data.objects:
                # Method A: use the data API
                obj = bpy.data.objects[object_to_delete.name]
                bpy.data.objects.remove(obj, do_unlink=True)

        # export STL with the correct operator
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
    PackingSimulation(parameters, suffix=suffix).run()


if __name__ == "__main__":
    main()
