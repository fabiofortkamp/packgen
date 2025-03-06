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
