"""Print summary of the mass fraction calculations."""

from dataclasses import dataclass

from rich import print
from rich.table import Table

from packgen.blend import number_ratio, volume_prism

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


def calculate_results(packings: list[Packing]) -> list[dict[str, float]]:
    results = []
    for packing in packings:
        volumes = volume_prism(N_SIDES, packing.radii, heights=packing.heights)
        nA, _ = packing.number_ratios()
        r = {
            "mass fraction A": packing.mass_ratio_A,
            "density A": packing.densities[0],
            "density B": packing.densities[1],
            "volume A": float(volumes[0]),
            "volume B": float(volumes[1]),
            "number ratio A": nA,
        }
        results.append(r)

    return results


def tabulate(results: list[dict[str, float]]) -> Table:
    table = Table()
    example = results[0]
    for name in example.keys():
        table.add_column(name)

    for r in results:
        table.add_row(
            str(r["mass fraction A"]),
            str(r["density A"]),
            str(r["density B"]),
            str(r["volume A"]),
            str(r["volume B"]),
            str(r["number ratio A"]),
        )

    return table


def main():
    """Generate and print table."""
    packings = [
        Packing(
            mass_ratio_A=0.5, densities=(1.0, 1.0), radii=(1.0, 1.0), heights=(1.0, 1.0)
        ),
        Packing(
            mass_ratio_A=0.5, densities=(0.5, 1.0), radii=(1.0, 1.0), heights=(1.0, 1.0)
        ),
        Packing(
            mass_ratio_A=0.5, densities=(1.0, 0.5), radii=(1.0, 1.0), heights=(1.0, 1.0)
        ),
    ]
    results = calculate_results(packings)
    print(tabulate(results))


if __name__ == "__main__":
    main()
