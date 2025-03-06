from packgen import blend
from math import sqrt, isclose


def test_volume_prism_coincides_with_hexagon():
    """Check volume calculation with known expression for hexagonal prisms"""

    r = 2.3
    h = 4.5
    V_actual = blend.volume_prism(6, r, h)

    # use expression for hexagonal prisms that are used of other parts of our codebase
    area_hexagon = 3 * sqrt(3) / 2 * r**2
    V_expected = area_hexagon * h
    assert isclose(V_expected, V_actual)


# Specification-based testing for the main geometry functions
#
# 1. volume_prism(sides, radii, heights) -> returns the volume of a prism with polygonal faces with
#   'sides' number of sides, circumscribed radius 'radii' and 'heights' as the normal height
#
# Some observations:
#
# - None of the values can be empty
# - All numerical values must be positive (input AND output)
# - Function should work for scalar inputs and return an scalar (COVERED BY THE TEST ABOVE)
# - If two of the inputs are scalar and the other a list/vector, then the output should match this length
#   and just cast the other two inputs
# - Mathematically, inputs are not symmetrical because results are obviously quadratic in radius but linear in height
# - Inputs should work with sequences and numpy arrays
# - Easy to compute cases: square and circle (number of sides really large).
#
# 2. number_ratio(mass_ratio, densities, heights, radii, total_mass):
#
# Specification: we are analyzing a packing of particles. Given an array of mass ratios, densities, heights and radii,
# where all these arrays have as many elements as the types of particles, and a total mass, this returns the ratio of the number of particles
# as well as the total number of each type of particle
#
# Some observations:
#
# - to make usage of the function clearer, all arguments except the last one should always be arrays or lists
# - Does this function actually work for more than two types of particles?
# - If the geometry of the particles are the same, then:
#   - If the particles have the same density, then the number ratio == mass ratio
#   - If A has half the density of B, to maintain a 50/50 mass_ratio A must have twice as many particles as B
# - The elements of mass ratio are actually not all independent
# - densities, radii, heights should always have the same length
# - If the densities are the same, and A has half the volume of B, then to maintain a 50/50 mass ratio, n(A) == 2n(B)
