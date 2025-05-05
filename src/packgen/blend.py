"""Run packing simulation in Blender.

Original design and implementation by Andrea Insinga.
"""

import array as arr
import random
import json
import bpy
import numpy as np
from numpy.typing import ArrayLike


def volume_prism(sides: ArrayLike, radii: ArrayLike, heights: ArrayLike) -> ArrayLike:
    """Return the volume of a prism with given number of sides, radius, and height.

    References:
        https://en.wikipedia.org/wiki/Regular_polygon
    """
    sides = np.array(sides)
    radii = np.array(radii)
    heights = np.array(heights)

    return 1 / 2 * sides * np.square(radii) * np.sin(2 * np.pi / sides) * heights


parameters_file = "parameters.json"
with open(parameters_file) as f:
    parameters = json.load(f)

GlobalScaleFactor = 2.5
CombinationsRadii = arr.array("d", [0.200 / 2, 0.059 / 2])
CombinationsHeights = arr.array("d", [0.0871, 0.027])
number_fraction_non_aligned = parameters["number_fraction_non_aligned"]
num_cubes_x = 2  # Number of cubes along the X axis
num_cubes_y = 2  # Number of cubes along the Y axis
num_cubes_z = 100  # Number of   cubes along the Z axis
distance = 1.5  # Distance between the cubes
seed = 42

# convention for indices for the "aligned" and "non-aligned" particles
I_ALIGNED = 0
I_NON_ALIGNED = 1
z0 = distance / 2
CombinationsFractions = arr.array(
    "d", [1.0 - number_fraction_non_aligned, number_fraction_non_aligned]
)
CombinationsCumSum = arr.array("d", [0.0, 0.0])
CombinationRed = arr.array("d", [0.1, 0.8])
CombinationGreen = arr.array("d", [0.8, 0.4])
CombinationBlue = arr.array("d", [0.7, 0.7])

num_cubes_total = num_cubes_x * num_cubes_y * num_cubes_z
num_cubes_non_aligned = round(number_fraction_non_aligned * num_cubes_total)
num_cubes_aligned = num_cubes_total - num_cubes_non_aligned

random.seed(seed)  # Optional: set a seed for reproducible results
TheSum = sum(CombinationsFractions)

# Normalize array
for i in range(len(CombinationsFractions)):
    CombinationsFractions[i] = CombinationsFractions[i] / TheSum

# Cumulative Sum
CumulativeSum = 0.0
for i in range(len(CombinationsFractions)):
    CumulativeSum = CumulativeSum + CombinationsFractions[i]
    CombinationsCumSum[i] = CumulativeSum


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


def decide_cube(n_non_aligned: int, n_aligned: int) -> int:
    """Decide which cube type to generate, based on how many were generated."""
    ThisRandomNumber = random.uniform(0.0, 1.0)
    LastI = -1
    for i in range(len(CombinationsFractions)):
        if ThisRandomNumber > CombinationsCumSum[i]:
            LastI = i
    LastI = LastI + 1
    return LastI


# Create an array of cubes with random sizes determined by the log-normal distribution
n_generated_cubes_non_aligned = 0
n_generated_cubed_aligned = 0
for x in range(num_cubes_x):
    for y in range(num_cubes_y):
        for z in range(num_cubes_z):
            LastI = decide_cube(
                n_generated_cubes_non_aligned, n_generated_cubed_aligned
            )

            if LastI == I_NON_ALIGNED:
                n_generated_cubes_non_aligned += 1
            else:
                n_generated_cubed_aligned += 1

            bpy.ops.mesh.primitive_cylinder_add(
                vertices=6,
                radius=GlobalScaleFactor * CombinationsRadii[LastI],
                depth=GlobalScaleFactor * CombinationsHeights[LastI],
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


def export_stl():
    stl_path = "packing.stl"

    print("Exporting to", stl_path)
    bpy.ops.wm.stl_export(filepath=stl_path)


def stop_playback(scene):
    if scene.frame_current == 230:
        bpy.ops.wm.save_mainfile(filepath="packing.blender")
        bpy.ops.screen.animation_cancel(restore_frame=False)
        bpy.ops.object.delete(use_global=False)
        export_stl()


bpy.app.handlers.frame_change_pre.append(stop_playback)
bpy.ops.screen.animation_play()
