"""Pure packing-simulation configuration and geometry logic."""

import json
import math
import random
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path


@dataclass(frozen=True)
class Parameters:
    """Typed view of the packing-simulation input JSON.

    Field names mirror the JSON keys so the file format is unchanged.
    """

    scale: float
    r_A: float
    r_B: float
    thickness_A: float
    thickness_B: float
    density_A: float
    density_B: float
    num_sides: int
    num_particles_x: int
    num_particles_y: int
    num_particles_z: int
    distance: float
    mass_fraction_B: float
    particle_friction: float
    particle_restitution: float
    particle_damping: float
    mass_piston: float
    end_frame: int
    use_piston: bool
    seed: float
    container_wall_thickness: float = -0.2
    container_piston_slack: float = 0.0
    gravity_field: tuple[float, float, float] = (0.0, 0.0, -9.8)
    save_blender_file: bool = True
    save_json_file: bool = True
    save_stl_file: bool = True
    quit_on_finish: bool = False

    @classmethod
    def from_json(cls, path: str | Path) -> "Parameters":
        """Load parameters from a JSON file.

        A ``seed`` of ``null`` is replaced with a freshly generated random
        value so the actually-used seed can be persisted on output.
        """
        with open(path) as f:
            raw = json.load(f)
        if raw.get("seed") is None:
            raw["seed"] = random.random() * 1e6
        if "gravity_field" in raw:
            raw["gravity_field"] = tuple(raw["gravity_field"])
        return cls(**raw)

    @property
    def num_particles_total(self) -> int:
        """Total number of particles in the initial grid."""
        return self.num_particles_x * self.num_particles_y * self.num_particles_z


class ParticleType(IntEnum):
    """Available particle material/geometry types."""

    INVALID = -1
    A = 0
    B = 1


PARTICLE_COLOR: dict[ParticleType, tuple[float, float, float]] = {
    ParticleType.A: (0.1, 0.8, 0.7),
    ParticleType.B: (0.8, 0.4, 0.7),
}


@dataclass(frozen=True)
class ParticleSpec:
    """Pure description of a particle Blender should create."""

    particle_type: ParticleType
    location: tuple[float, float, float]
    rotation: tuple[float, float, float]
    radius: float
    height: float
    mass: float
    friction: float
    restitution: float
    damping: float


@dataclass(frozen=True)
class PistonSpec:
    """Pure description of the optional piston."""

    enabled: bool
    side_length: float
    z: float
    mass: float


@dataclass(frozen=True)
class ContainerSpec:
    """Pure description of the container Blender should create."""

    side_length: float
    height: float
    wall_thickness: float


@dataclass(frozen=True)
class PackingSpec:
    """Pure description of a packing simulation run."""

    parameters: Parameters
    particles: tuple[ParticleSpec, ...]
    piston: PistonSpec
    container: ContainerSpec
    gravity: tuple[float, float, float]
    frame_start: int
    frame_end: int


def volume_prism(sides: float, radius: float, height: float) -> float:
    """Return the volume of a prism with given number of sides, radius, and height.

    References:
        https://en.wikipedia.org/wiki/Regular_polygon

    """
    return 1 / 2 * sides * radius * radius * math.sin(2 * math.pi / sides) * height


def num_B_particles(parameters: Parameters, num_particles_total: int) -> int:
    """Return the total number of type-B particles to be generated."""
    V_B = volume_prism(parameters.num_sides, parameters.r_B, parameters.thickness_B)
    V_A = volume_prism(parameters.num_sides, parameters.r_A, parameters.thickness_A)

    beta = parameters.density_B * V_B / (parameters.density_A * V_A)

    x_B = parameters.mass_fraction_B
    alpha = 1 / beta * (x_B / (1 - x_B))

    N_B = alpha / (1 + alpha) * num_particles_total

    return math.ceil(N_B)


def particle_density(parameters: Parameters, particle_type: ParticleType) -> float:
    """Return the bulk density of a particle of the given type."""
    if particle_type == ParticleType.B:
        return parameters.density_B
    return parameters.density_A


def particle_dimensions(
    parameters: Parameters, particle_type: ParticleType
) -> tuple[float, float]:
    """Return (scaled circumscribed radius, scaled height) for the given type."""
    radii = (parameters.r_A, parameters.r_B)
    heights = (parameters.thickness_A, parameters.thickness_B)
    return (
        parameters.scale * radii[particle_type],
        parameters.scale * heights[particle_type],
    )


def particle_mass(parameters: Parameters, particle_type: ParticleType) -> float:
    """Return the rigid-body mass of a particle of the given type."""
    radius, height = particle_dimensions(parameters, particle_type)
    volume = volume_prism(parameters.num_sides, radius, height)
    return particle_density(parameters, particle_type) * volume


def decide_particle_type(
    number_fraction_A: float, rng: random.Random | None = None
) -> ParticleType:
    """Pick A or B by sampling one uniform draw against the target A fraction."""
    draw = random.uniform(0.0, 1.0) if rng is None else rng.uniform(0.0, 1.0)
    if draw > number_fraction_A:
        return ParticleType.B
    return ParticleType.A


def build_packing_spec(parameters: Parameters) -> PackingSpec:
    """Return a pure specification of the Blender packing simulation."""
    rng = random.Random(parameters.seed)
    n_B = num_B_particles(parameters, parameters.num_particles_total)
    number_fraction_A = 1 - n_B / parameters.num_particles_total
    piston = _build_piston_spec(parameters)
    particles = tuple(
        _build_particle_spec(location, parameters, number_fraction_A, rng)
        for location in _particle_locations(parameters)
    )
    return PackingSpec(
        parameters=parameters,
        particles=particles,
        piston=piston,
        container=_build_container_spec(parameters, piston),
        gravity=parameters.gravity_field,
        frame_start=1,
        frame_end=parameters.end_frame,
    )


def _build_piston_spec(parameters: Parameters) -> PistonSpec:
    L_container = parameters.num_particles_x * parameters.distance
    max_z_particles = parameters.distance / 2 + parameters.num_particles_z * (
        parameters.distance
    )
    side_length = (1 - parameters.container_piston_slack) * L_container
    z = 1.1 * max_z_particles + side_length / 2
    return PistonSpec(
        enabled=parameters.use_piston,
        side_length=side_length,
        z=z,
        mass=parameters.mass_piston,
    )


def _build_container_spec(
    parameters: Parameters, piston: PistonSpec
) -> ContainerSpec:
    side_length = parameters.num_particles_x * parameters.distance
    height = 1.1 * (piston.z + piston.side_length / 2)
    return ContainerSpec(
        side_length=side_length,
        height=height,
        wall_thickness=parameters.container_wall_thickness,
    )


def _particle_locations(
    parameters: Parameters,
) -> tuple[tuple[float, float, float], ...]:
    distance = parameters.distance
    z0 = distance / 2
    return tuple(
        (
            (ix - parameters.num_particles_x / 2 + 0.5) * distance,
            (iy - parameters.num_particles_y / 2 + 0.5) * distance,
            z0 + iz * distance,
        )
        for ix in range(parameters.num_particles_x)
        for iy in range(parameters.num_particles_y)
        for iz in range(parameters.num_particles_z)
    )


def _build_particle_spec(
    location: tuple[float, float, float],
    parameters: Parameters,
    number_fraction_A: float,
    rng: random.Random,
) -> ParticleSpec:
    particle_type = decide_particle_type(number_fraction_A, rng)
    radius, height = particle_dimensions(parameters, particle_type)
    return ParticleSpec(
        particle_type=particle_type,
        location=location,
        rotation=(
            rng.uniform(0, 2 * math.pi),
            rng.uniform(0, 2 * math.pi),
            rng.uniform(0, 2 * math.pi),
        ),
        radius=radius,
        height=height,
        mass=particle_mass(parameters, particle_type),
        friction=parameters.particle_friction,
        restitution=parameters.particle_restitution,
        damping=parameters.particle_damping,
    )
