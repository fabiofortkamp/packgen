# Script by Andrea Insinga

# this enables testing the top-level functions
# in environments without Blender
try:
    import bpy
except ImportError:
    bpy = None
import random
import array as arr
import numpy as np


def volume_prism(sides, radii, heights):
    # https://en.wikipedia.org/wiki/Regular_polygon

    sides = np.array(sides)
    radii = np.array(radii)
    heights = np.array(heights)

    return 1 / 2 * sides * np.square(radii) * np.sin(2 * np.pi / sides) * heights


# Mass fractions
def number_ratio(mass_ratio, densities, heights, radii, total_volume):
    """
    Calculate the number ratio of the materials in the mixture given the mass ratio, densities, volumes and total mass of the components.
    """

    # Calculate the volumes of each particle
    particle_volumes = volume_prism([6] * len(radii), radii, heights)

    # What percentage of the total mass is taken by each type of particle in the mixture?
    mass_percentages = [x / sum(mass_ratio) for x in mass_ratio]

    sum_of_densities = sum([density for density, mass_ratio_i in zip(densities, mass_ratio) 
                            if mass_ratio_i > 0
                            ])

    volume_ratios = [
        x / (y / sum_of_densities) for x, y in zip(mass_percentages, densities)
    ]

    volume_percentages = np.array(volume_ratios) / sum(volume_ratios)

    volume_components = volume_percentages * total_volume

    number_components = [
        x / y for x, y in zip(volume_components, particle_volumes)
    ]

    # must round up or down to the nearest integer
    number_components_rounded = [
        int(np.ceil(x / y)) for x, y in zip(volume_components, particle_volumes)
    ]

    print(number_components_rounded, number_components)
    for x, y in zip(number_components_rounded, number_components):
        # Check if the relative error is larger than 0.1%
        rel_diff = abs(x - y) / y
        if rel_diff > 0.001:
            raise Warning("The relative error due to rounding is larger than 0.1%.")

    number_percentages_rounded = [x / sum(number_components_rounded) for x in number_components_rounded]

    return number_percentages_rounded, number_components_rounded


# 1) Select "Scripting" workspace
# 2) In the "Text Editor" window, open this script and click "Run Script"
# 3) Select "Animation" workspace
# 4) In the "Timeline" press "Play"
# 5) Erase the cube and export as stl.

# The two arrays must be the same number of elements
# (they represent COMBINATIONS of radius and height)
CombinationsRadii = arr.array(
    "d", [0.1, 0.1, 0.1]
)
CombinationsHeights = arr.array(
    "d", [0.2, 0.2, 0.2]
)


CombinationsMassFractions = arr.array(
    "d", [1.0, 1.0, 1.0]
)
CombinationDensities = arr.array("d", [1.0, 1.0, 1.0])
TotalVolume = 30

CombinationsFractions, CombinationsPopulations = number_ratio(
    CombinationsMassFractions,
    CombinationDensities,
    CombinationsHeights,
    CombinationsRadii,
    TotalVolume
)

# CombinationsFractions = arr.array("d", [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0])
CombinationsCumSum = arr.array("d", [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
CombinationRed = arr.array("d", [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0])
CombinationGreen = arr.array("d", [0.0, 0.0, 0.0, 0.0, 0.6, 0.0, 0.0, 0.0, 0.8])
CombinationBlue = arr.array("d", [0.0, 0.0, 0.0, 0.0, 0.7, 0.0, 0.0, 0.0, 0.5])
TheSum = sum(CombinationsFractions)

# Normalize array
for i in range(len(CombinationsFractions)):
    CombinationsFractions[i] = CombinationsFractions[i] / TheSum

# Cumulative Sum
CumulativeSum = 0.0
for i in range(len(CombinationsFractions)):
    CumulativeSum = CumulativeSum + CombinationsFractions[i]
    CombinationsCumSum[i] = CumulativeSum


# Container box
def create_cube_without_top_face(thesize):
    scale_z = 3
    bpy.ops.mesh.primitive_cube_add(
        size=thesize, enter_editmode=False, location=(0, 0, 0), scale=(1, 1, scale_z)
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

def generate_cylinders_grid():
    # Customize the following parameters for your array of cubes
    num_cubes_x = 2  # Number of cubes along the X axis
    num_cubes_y = 2  # Number of cubes along the Y axis
    num_cubes_z = 50  # Max number of   cubes along the Z axis
    total_number = sum(CombinationsPopulations)

    distance = 2.5  # Distance between the cubes
    mu = 0  # Mean of the log-normal distribution
    sigma = 0.1  # Standard deviation of the log-normal distribution
    random.seed(42)  # Optional: set a seed for reproducible results

    # Delete all existing mesh objects
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.object.select_by_type(type="MESH")
    bpy.ops.object.delete()

    # Create an array of cubes with random sizes determined by the log-normal distribution
    count = 0
    for x in range(num_cubes_x):
        for y in range(num_cubes_y):
            for z in range(num_cubes_z):
                ThisRandomNumber = random.uniform(0.0, 1.0)
                LastI = -1
                for i in range(len(CombinationsFractions)):
                    if ThisRandomNumber > CombinationsCumSum[i]:
                        LastI = i
                LastI = LastI + 1

                bpy.ops.mesh.primitive_cylinder_add(
                    vertices=6,
                    radius= CombinationsRadii[LastI],
                    depth= CombinationsHeights[LastI],
                    enter_editmode=False,
                    location=(
                        (x - num_cubes_x / 2 + 0.5) * distance,
                        (y - num_cubes_y / 2 + 0.5) * distance,
                        z * distance,
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

                if count == total_number:
                    break

def generate_cylinders_random(N, a, cube_thickness):
    # Customize the following parameters for your array of cubes
    random.seed(42)  # Optional: set a seed for reproducible results

    # Delete all existing mesh objects
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.object.select_by_type(type="MESH")
    bpy.ops.object.delete()

    for n in range(N):
        ThisRandomNumber = random.uniform(0.0, 1.0)
        LastI = -1
        for i in range(len(CombinationsFractions)):
            if ThisRandomNumber > CombinationsCumSum[i]:
                LastI = i
        LastI = LastI + 1

        max_height = max(CombinationsHeights)
        max_radius = max(CombinationsRadii)
        self_avoidance = np.sqrt(max_radius**2 + (max_height/2)**2)

        # Generation square should be smaller than the cube so the cylinders do not touch the walls
        generation_a = a - self_avoidance - cube_thickness

        bpy.ops.mesh.primitive_cylinder_add(
            vertices=6,
            radius= CombinationsRadii[LastI],
            depth= CombinationsHeights[LastI],
            enter_editmode=False,
            location=(
                random.uniform(-generation_a, generation_a) / 2,
                random.uniform(-generation_a, generation_a) / 2,
                (n + 1) * self_avoidance,
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

def main():
    print("total number", sum(CombinationsPopulations))
    
    thickness = -0.2

    generate_cylinders_random(sum(CombinationsPopulations), a, np.abs(thickness))

    cube = create_cube_without_top_face(a)
    add_solidify_modifier(cube, thickness)

    add_passive_rigidbody(cube)


if __name__ == "__main__":
    main()
