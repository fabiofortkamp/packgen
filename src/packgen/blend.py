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
import sys
from pathlib import Path

import bpy
import numpy as np


def get_parameters_file() -> str:
    """Parse argument lists and return parameters file name."""
    if "--" in sys.argv:
        argv = sys.argv[sys.argv.index("--") + 1 :]  # get all args after "--"
        parameters_file = argv[0]
    else:
        parameters_file = "parameters.json"
    return parameters_file


def load_parameters(parameters_file: str = "parameters.json") -> dict[str, float]:
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
    return 1 / 2 * sides * np.square(radius) * np.sin(2 * np.pi / sides) * height


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


parameters = load_parameters(get_parameters_file())
scale = parameters["scale"]

# convention for indices for the "A" and "non-A" particles
I_B = 1

radii = arr.array("d", [parameters["r_A"], parameters["r_B"]])
heights = arr.array("d", [parameters["thickness_A"], parameters["thickness_B"]])

num_cubes_x = int(parameters["num_cubes_x"])  # Number of cubes along the X axis
num_cubes_y = int(parameters["num_cubes_y"])  # Number of cubes along the Y axis
num_cubes_z = int(parameters["num_cubes_z"])  # Number of cubes along the Z axis
num_cubes_total = num_cubes_x * num_cubes_y * num_cubes_z
num_cubes_B = num_B_particles(parameters, num_cubes_total)
number_fraction_B = num_cubes_B / num_cubes_total
distance = parameters["distance"]  # Distance between the cubes
seed = parameters["seed"]

z0 = distance / 2
number_fractions = arr.array("d", [1.0 - number_fraction_B, number_fraction_B])
cum_sums = arr.array("d", [0.0, 0.0])
CombinationRed = arr.array("d", [0.1, 0.8])
CombinationGreen = arr.array("d", [0.8, 0.4])
CombinationBlue = arr.array("d", [0.7, 0.7])

random.seed(seed)  # Optional: set a seed for reproducible results
the_sum = sum(number_fractions)

# Normalize array
for i in range(len(number_fractions)):
    number_fractions[i] = number_fractions[i] / the_sum

# Cumulative Sum
cum_sum = 0.0
for i in range(len(number_fractions)):
    cum_sum = cum_sum + number_fractions[i]
    cum_sums[i] = cum_sum


def create_cube_without_top_face(side: float, height: float):
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

    return cube


def add_solidify_modifier(cube, thickness):
    modifier = cube.modifiers.new(name="Solidify", type="SOLIDIFY")
    modifier.thickness = thickness


def add_passive_rigidbody(cube):
    bpy.ops.rigidbody.object_add(type="PASSIVE")
    cube.rigid_body.collision_shape = "MESH"


# Delete all existing mesh objects
bpy.ops.object.select_all(action="DESELECT")
bpy.ops.object.select_by_type(type="MESH")
bpy.ops.object.delete()


def decide_cube(n_B: int, n_A: int) -> int:
    """Decide which cube type to generate, based on how many were generated."""
    ThisRandomNumber = random.uniform(0.0, 1.0)
    LastI = -1
    for i in range(len(number_fractions)):
        if ThisRandomNumber > cum_sums[i]:
            LastI = i
    LastI = LastI + 1
    return LastI


n_sides = parameters["num_sides"]
# Create an array of cubes with random sizes determined by the log-normal distribution
n_generated_cubes_B = 0
n_generated_cubed_A = 0
for x in range(num_cubes_x):
    for y in range(num_cubes_y):
        for z in range(num_cubes_z):
            LastI = decide_cube(n_generated_cubes_B, n_generated_cubed_A)

            if LastI == I_B:
                n_generated_cubes_B += 1
            else:
                n_generated_cubed_A += 1

            bpy.ops.mesh.primitive_cylinder_add(
                vertices=n_sides,
                radius=scale * radii[LastI],
                depth=scale * heights[LastI],
                enter_editmode=False,
                location=(
                    (x - num_cubes_x / 2 + 0.5) * distance,
                    (y - num_cubes_y / 2 + 0.5) * distance,
                    z0 + z * distance,
                ),
            )

            # Get the active object (the newly created cube)
            cube = bpy.context.active_object

            # Assign a random rotation to the cube
            cube.rotation_euler = (
                random.uniform(0, 6.283185),
                random.uniform(0, 6.283185),
                random.uniform(0, 6.283185),
            )

            # Add rigid body physics to the cube
            bpy.ops.rigidbody.object_add(type="ACTIVE")
            cube.rigid_body.friction = 0.5
            cube.rigid_body.restitution = 0.5

            mat = bpy.data.materials.new("PKHG")
            mat.diffuse_color = (
                float(CombinationRed[LastI]),
                float(CombinationGreen[LastI]),
                float(CombinationBlue[LastI]),
                1.0,
            )
            mat.specular_intensity = 0

            cube.active_material = mat

thickness = -0.2

cube = create_cube_without_top_face((num_cubes_x) * distance, num_cubes_z * distance)
add_solidify_modifier(cube, thickness)

add_passive_rigidbody(cube)


def get_params_suffix() -> str:
    """Get the base name of the parameters file without extension to use as a suffix.

    Returns:
        str: The base name of the parameters file without extension.
    """
    return Path(get_parameters_file()).stem


def export_stl():
    stl_path = f"packing_{get_params_suffix()}.stl"

    print("Exporting to", stl_path)
    bpy.ops.wm.stl_export(filepath=stl_path)


def stop_playback(scene):
    if scene.frame_current == 230:
        bpy.ops.wm.save_mainfile(filepath=f"packing_{get_params_suffix()}.blender")
        bpy.ops.screen.animation_cancel(restore_frame=False)
        bpy.ops.object.delete(use_global=False)
        export_stl()


bpy.app.handlers.frame_change_pre.append(stop_playback)
bpy.ops.screen.animation_play()
