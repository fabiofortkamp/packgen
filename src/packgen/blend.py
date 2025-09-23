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
import random
from typing import Any
import sys
from pathlib import Path
from enum import IntEnum

import os
import bpy


def get_parameters_file() -> str:
    """Parse argument lists and return parameters file name."""
    if "--" in sys.argv:
        argv = sys.argv[sys.argv.index("--") + 1:]  # get all args after "--"
        parameters_file = argv[0]
    else:
        parameters_file = "parameters.json"
    return parameters_file


def get_params_suffix() -> str:
    """Get the base name of the parameters file without extension to use as a suffix.

    Returns:
        str: The base name of the parameters file without extension.

    """
    return Path(get_parameters_file()).stem


def load_parameters(
        parameters_file: str = "parameters.json",
) -> dict[str, float | bool]:
    """Load parameters from a JSON file.

    Args:
        parameters_file (str): Path to the parameters file.
            Defaults to "parameters.json".

    Returns:
        dict[str, float]: The loaded parameters mapping strings to float values.
            If 'seed' is null in the JSON, it will be converted to a random float.

    """
    with open(parameters_file) as f:
        params = json.load(f)
        if params.get("seed") is None:
            params["seed"] = random.random() * 1e6
        return params


def volume_prism(sides: float, radius: float, height: float) -> float:
    """Return the volume of a prism with given number of sides, radius, and height.

    References:
        https://en.wikipedia.org/wiki/Regular_polygon

    """
    return 1 / 2 * sides * radius * radius * math.sin(2 * math.pi / sides) * height


def num_B_particles(parameters: dict[str, float], num_particles_total: int) -> int:
    """Return the total number of type-B particles to be generated.

    Args:
        parameters (dict[str, float]): The parameters of the packing simulation.
        num_particles_total (int): The total number of particles to be generated.

    """
    rho_B = parameters["density_B"]
    rho_A = parameters["density_A"]

    r_B = parameters["r_B"]
    r_A = parameters["r_A"]

    h_B = parameters["thickness_B"]
    h_A = parameters["thickness_A"]

    n_sides = int(parameters["num_sides"])
    V_B = volume_prism(n_sides, r_B, h_B)
    V_A = volume_prism(n_sides, r_A, h_A)

    beta = rho_B * V_B / (rho_A * V_A)

    x_B = parameters["mass_fraction_B"]
    alpha = 1 / beta * (x_B / (1 - x_B))

    N_B = alpha / (1 + alpha) * num_particles_total

    return math.ceil(N_B)


class ParticleType(IntEnum):
    INVALID = -1
    A = 0
    B = 1


class Particle:

    def __init__(self, x: float, y: float, z: float, parameters) -> None:
        self.parameters = parameters
        particle_type = self.decide_particle_type()
        self.type = particle_type
        if self.type == ParticleType.B:
            density = parameters["density_B"]
        else:
            density = parameters["density_A"]

        radii = arr.array("d", [parameters["r_A"], parameters["r_B"]])
        heights = arr.array("d", [parameters["thickness_A"], parameters["thickness_B"]])
        n_sides = parameters["num_sides"]
        scale = parameters["scale"]
        particle_volume = volume_prism(n_sides, scale * radii[particle_type], scale * heights[particle_type])

        bpy.ops.mesh.primitive_cylinder_add(
            vertices=n_sides,
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
        particle.rigid_body.friction = parameters["particle_friction"]
        particle.rigid_body.restitution = parameters["particle_restitution"]
        particle.rigid_body.mass = density * particle_volume
        particle.rigid_body.linear_damping = parameters["particle_damping"]
        mat = bpy.data.materials.new("GenericMaterial")
        mat.diffuse_color = (
            float(COMBINATION_RED[particle_type]),
            float(COMBINATION_GREEN[particle_type]),
            float(COMBINATION_BLUE[particle_type]),
            1.0,
        )
        mat.specular_intensity = 0
        particle.active_material = mat

    def decide_particle_type(self) -> ParticleType:
        """Decide which cube type to generate."""
        parameters = self.parameters
        num_particles_x = int(parameters["num_particles_x"])  # Number of cubes along the X axis
        num_particles_y = int(parameters["num_particles_y"])  # Number of cubes along the Y axis
        num_particles_z = int(parameters["num_particles_z"])  # Number of cubes along the Z axis
        num_particles_total = num_particles_x * num_particles_y * num_particles_z
        num_particles_B = num_B_particles(parameters, num_particles_total)
        number_fraction_B = num_particles_B / num_particles_total
        rnd = random.uniform(0.0, 1.0)
        particle_type = ParticleType.A

        number_fraction_A = 1 - number_fraction_B
        if rnd > number_fraction_A:
            # if we are supposed to generate only 20% of A,
            # and we randomly select a number bigger than that,
            # then we must generate the other type
            particle_type = ParticleType.B

        return particle_type


class Container:
    def __init__(self,
                 side: float, height: float
                 ) -> None:
        """Create an open cube-like container of given side length and height.

        Args:
            side (float): The length of the sides of the cube.
            height (float): The height of the container.

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

        modifier.thickness = PARAMETERS.get("container_wall_thickness", -0.2)

        bpy.ops.rigidbody.object_add(type="PASSIVE")
        cube.rigid_body.collision_shape = "MESH"
        cube.name = "Container"
        self.name = cube.name


class Piston:
    def __init__(self, L_container, max_z_particles, parameters) -> None:
        slack = PARAMETERS.get("container_piston_slack", 0.0)
        L_piston = (1 - slack) * L_container
        z_piston = 1.1 * max_z_particles + L_piston / 2
        
        if parameters["use_piston"]:
            bpy.ops.mesh.primitive_cube_add(
                size=L_piston,
                enter_editmode=False,
                align='WORLD',
                location=(0, 0, z_piston),
                scale=(1, 1, 1))
                
            piston = bpy.context.active_object
            bpy.ops.rigidbody.object_add(type="ACTIVE")
            piston.rigid_body.friction = 0  # piston does not lose velocity when colliding
            piston.rigid_body.restitution = 0  # piston does not bounce when colliding
            piston.rigid_body.mass = parameters["mass_piston"]
            piston.name = "Piston"
        
        self.z = z_piston
        self.L = L_piston










PARAMETERS = {
    "seed": 42,
    "scale": 1.0,
    "r_B": 0.0295,
    "r_A": 0.1,
    "thickness_B": 0.027,
    "thickness_A": 0.0871,
    "density_B": 15.1,
    "density_A": 5.1,
    "mass_fraction_B": 0.20,
    "num_particles_x": 2,
    "num_particles_y": 2,
    "num_particles_z": 200,
    "num_sides": 6,
    "distance": 0.6,
    "quit_on_finish": False,
    "mass_piston": 1,
    "particle_restitution": 0.5,  # how much objects bounce after collision
    "particle_friction": 0.8,  # fraction of velocity that is lost after collision
    "particle_damping": 0.8,  # fraction of linear velocity that is lost over time
    "save_files": False,
    "container_wall_thickness": -0.2,
    "container_piston_slack": 0.01,
    "gravity_field": [0, 0, -30],
    "end_frame":250,
    "use_piston": True,
}

COMBINATION_RED = arr.array("d", [0.1, 0.8])
COMBINATION_GREEN = arr.array("d", [0.8, 0.4])
COMBINATION_BLUE = arr.array("d", [0.7, 0.7])


class PackingSimulation:
    """Packing simulation to be performed with the physics-engine."""

    def __init__(self, parameters: dict[str, Any]) -> None:
        self.parameters = parameters
        self._clean_state()
        self._initialize_random_state()

    def run(self):
        """Run the particle packing simulation."""  # noqa: D401

        self._initialize_particles()

        piston = self._initialize_piston()
        container = self._initialize_container(piston)

        self.bake_and_export(end_frame=self.parameters["end_frame"], container=container)

    def _initialize_piston(self) -> Piston:
        parameters = self.parameters
        num_particles_x = int(parameters["num_particles_x"])  # Number of cubes along the X axis
        num_particles_z = int(parameters["num_particles_z"])  # Number of cubes along the Y axis
        distance = parameters["distance"]  # Distance between the cubes
        L_container = num_particles_x * distance
        z0 = distance / 2
        max_z_particles = z0 + num_particles_z * distance
        # add piston
        piston = Piston(L_container,max_z_particles,parameters)
        return piston

    def _initialize_container(self,piston) -> Container:
        # create container
        z_piston = piston.z
        L_piston = piston.L
        num_particles_x = self.parameters["num_particles_x"]
        distance = self.parameters["distance"]
        Lxy = num_particles_x * distance
        Lz = 1.1 * (z_piston + L_piston / 2)
        container = Container(Lxy,Lz)
        return container

    def _initialize_particles(self):
        n_generated_particles_B = 0
        n_generated_particles_A = 0
        parameters = self.parameters
        num_particles_x = int(parameters["num_particles_x"])  # Number of cubes along the X axis
        num_particles_y = int(parameters["num_particles_y"])  # Number of cubes along the Y axis
        num_particles_z = int(parameters["num_particles_z"])  # Number of cubes along the Z axis
        distance = parameters["distance"]  # Distance between the cubes
        z0 = distance / 2
        for ix in range(num_particles_x):
            for iy in range(num_particles_y):
                for iz in range(num_particles_z):
                    x = (ix - num_particles_x / 2 + 0.5) * distance
                    y = (iy - num_particles_y / 2 + 0.5) * distance
                    z = z0 + iz * distance
                    particle = Particle(x, y, z, parameters)

                    if particle.type == ParticleType.A:
                        n_generated_particles_A += 1
                    else:
                        n_generated_particles_B += 1

    @staticmethod
    def _clean_state():
        # Delete all existing mesh objects
        bpy.ops.object.select_all(action="DESELECT")
        bpy.ops.object.select_by_type(type="MESH")
        bpy.ops.object.delete()

    def _initialize_random_state(self):
        seed = self.parameters["seed"]
        random.seed(seed)

    def bake_and_export(self, end_frame: int, container: Any = None, ) -> None:
        """Bake the physics simulation and export the results.

        Args:
            end_frame (int): The last frame to bake the simulation to.
            container: The container of the particles that should be removed.
                If None, no object will be removed.

        """

        scene = bpy.context.scene
        # set the frame range
        scene.frame_start = 1
        scene.frame_end = end_frame

        # setting gravity
        parameters = self.parameters
        g = parameters.get("gravity_field", [0, 0, -9.8])
        scene.gravity = g

        # free any old bake, then bake all caches
        if scene.rigidbody_world:
            bpy.ops.ptcache.free_bake_all()
            bpy.ops.ptcache.bake_all()

        # step to the last frame so all transforms are final
        scene.frame_set(end_frame)

        # Use the current working directory for all output files
        stl_path: Path | None = None
        if parameters.get("save_files", True):
            output_dir = Path(os.getcwd())
            suffix = get_params_suffix()
            blend_path = output_dir / f"packing_{suffix}.blend"
            json_path = output_dir / f"packing_{suffix}.json"
            stl_path = output_dir / f"packing_{suffix}.stl"

            bpy.ops.wm.save_mainfile(filepath=str(blend_path))

            with open(json_path, mode="w") as f:
                json.dump(parameters, f)

        # the container deletion should occur after the main saving above
        # to be able to inspect the Blender file
        if container and container.name in bpy.data.objects:
            # Method A: use the data API
            obj = bpy.data.objects[container.name]
            bpy.data.objects.remove(obj, do_unlink=True)

        # export STL with the correct operator
        if parameters.get("save_files", True):
            if stl_path is not None:
                bpy.ops.wm.stl_export(filepath=str(stl_path))
            # if it is None, then something wrong happened and,
            # to avoid crashing, we simply don't save

        if parameters.get("quit_on_finish", False):
            bpy.ops.wm.quit_blender()


if __name__ == "__main__":
    PackingSimulation(PARAMETERS).run()
