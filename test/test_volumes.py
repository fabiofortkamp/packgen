"""Tests for the volumetric calculations."""

from math import isclose, sqrt

from packgen import blend


def test_volume_prism_coincides_with_hexagon() -> None:
    """Check volume calculation with known expression for hexagonal prisms."""
    r = 2.3
    h = 4.5
    V_actual = blend.volume_prism(6, r, h)

    # use expression for hexagonal prisms that are used of other parts of our codebase
    area_hexagon = 3 * sqrt(3) / 2 * r**2
    V_expected = area_hexagon * h
    assert isclose(V_expected, V_actual)


# Specification-based testing for the main geometry functions
#
# 1. volume_prism(sides, radius, height) -> returns the volume of a prism with polygonal
#   faces with 'sides' number of sides, circumscribed radius 'radius' and 'height'
#   as the normal height
#
# Some observations:
#
# - None of the values can be empty
# - All numerical values must be positive (input AND output)
# - Function should work for scalar inputs and return an scalar
#   (COVERED BY THE TEST ABOVE)
# - If two of the inputs are scalar and the other a list/vector, then the output should
#   match this length and just cast the other two inputs
# - Mathematically, inputs are not symmetrical because results are obviously quadratic
#   in radius but linear in height
# - Inputs should work with sequences and numpy arrays
# - Easy to compute cases: square and circle (number of sides really large).
