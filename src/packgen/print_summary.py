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

    def number_ratios(self) -> ParticlesValues:
        """Return number fraction of the packing.

        Assumes unitary total mass.
        """
        number_ratios, _ = number_ratio(
            mass_ratio=(self.mass_ratio_A, 1.0 - self.mass_ratio_A),
            densities=self.densities,
            radii=self.radii,
            heights=self.heights,
            total_mass=1.0,
        )
        return (number_ratios[0], number_ratios[1])


def main():
    """Generate and print table."""
    packings = [
        Packing(
            mass_ratio_A=0.5, densities=(1.0, 1.0), radii=(1.0, 1.0), heights=(1.0, 1.0)
        )
    ]
    for packing in packings:
        print(packing.number_ratios())


if __name__ == "__main__":
    main()

