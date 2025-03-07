"""Print summary of the mass fraction calculations."""

from packgen.blend import number_ratio

from dataclasses import dataclass

type ParticlesValues = tuple[float, float]

N_SIDES = 6


@dataclass
class Packing:
    """Configuration about packing of two types of particles."""

    mass_ratio_A: float
    densities: ParticlesValues
    radii: ParticlesValues
    heights: ParticlesValues


def main():
    """Generate and print table."""
    packings = [
        Packing(
            mass_ratio_A=0.5, densities=(1.0, 1.0), radii=(1.0, 1.0), heights=(1.0, 1.0)
        )
    ]
    print(packings)


if __name__ == "__main__":
    main()

