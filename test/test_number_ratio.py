import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import array as arr
from math import isclose

from packgen import blend


def test_number_ratio_same_density_and_geometry():
    """Check the resulting number ratio is the same as the mass ratio."""

    CombinationsRadii = arr.array(
        "d", [0.0600, 0.0600, 0.0600, 0.0600]
    )
    CombinationsHeights = arr.array(
        "d", [0.0500, 0.0500, 0.0500, 0.0500]
    )

    CombinationsMassFractions = arr.array(
        "d", [1, 2, 3, 4]
    )

    CombinationMassFractionsNormalized = [x / sum(CombinationsMassFractions) for x in CombinationsMassFractions] 
    CombinationDensities = arr.array("d", [1.0, 1.0, 1.0, 1.0])

    CombinationsFractions = blend.number_ratio(
        CombinationsMassFractions,
        CombinationDensities,
        CombinationsHeights,
        CombinationsRadii
        )

    CombinationFractionsNormalized = [
        x / sum(CombinationsFractions) for x in CombinationsFractions
    ]

    for x, y in zip(CombinationFractionsNormalized, CombinationMassFractionsNormalized):
        assert isclose(x, y, rel_tol=1e-4)


def test_number_ratio_half_density_same_geometry():
    """The resulting number ratio should have twice as many particles of the half density type."""

    CombinationsRadii = arr.array("d", [0.0600, 0.0600])
    CombinationsHeights = arr.array("d", [0.0500, 0.0500])

    CombinationsMassFractions = arr.array("d", [1, 1])

    CombinationDensities = arr.array("d", [0.8, 1.6])

    CombinationsFractions = blend.number_ratio(
        CombinationsMassFractions,
        CombinationDensities,
        CombinationsHeights,
        CombinationsRadii
        )

    assert isclose(
        CombinationsFractions[0],
        2 * CombinationsFractions[1],
        rel_tol=1e-4,
    )


def test_number_ratio_same_density_same_mass_half_height():
    """The resulting number ratio should have twice as many particles of the half height type."""

    CombinationsRadii = arr.array("d", [0.0600, 0.0600])
    CombinationsHeights = arr.array("d", [0.0500, 0.1000])

    CombinationsMassFractions = arr.array("d", [1, 1])

    CombinationDensities = arr.array("d", [1.6, 1.6])

    CombinationsFractions = blend.number_ratio(
        CombinationsMassFractions,
        CombinationDensities,
        CombinationsHeights,
        CombinationsRadii
    )

    assert isclose(
        CombinationsFractions[0],
        2 * CombinationsFractions[1],
        rel_tol=1e-4,
    )
