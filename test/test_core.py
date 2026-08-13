"""Tests for pure packing configuration and geometry logic."""

import json
import random
from math import isclose, pi, sqrt
from pathlib import Path

import pytest

from packgen import core


def _minimal_raw_parameters() -> dict[str, object]:
    """Smallest JSON-shaped dict that satisfies all required Parameters fields."""
    return {
        "scale": 1.0,
        "r_A": 0.1,
        "r_B": 0.05,
        "thickness_A": 0.08,
        "thickness_B": 0.03,
        "density_A": 5.0,
        "density_B": 15.0,
        "num_sides": 6,
        "num_particles_x": 2,
        "num_particles_y": 3,
        "num_particles_z": 4,
        "distance": 1.5,
        "mass_fraction_B": 0.5,
        "particle_friction": 0.8,
        "particle_restitution": 0.5,
        "particle_damping": 0.8,
        "mass_piston": 1.0,
        "end_frame": 700,
        "use_piston": True,
        "seed": 42,
    }


def _parameters(**overrides: object) -> core.Parameters:
    return core.Parameters(**(_minimal_raw_parameters() | overrides))  # type: ignore[arg-type]


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload))
    return path


def test_volume_prism_coincides_with_hexagon() -> None:
    """Check volume calculation with known expression for hexagonal prisms."""
    radius = 2.3
    height = 4.5

    volume_actual = core.volume_prism(6, radius, height)

    area_hexagon = 3 * sqrt(3) / 2 * radius**2
    volume_expected = area_hexagon * height
    assert isclose(volume_expected, volume_actual)


def test_parameters_from_json_preserves_seed(tmp_path: Path) -> None:
    """A numeric seed in the JSON is loaded verbatim."""
    payload = _minimal_raw_parameters() | {"seed": 12345}
    parameters = core.Parameters.from_json(_write_json(tmp_path / "p.json", payload))
    assert parameters.seed == 12345


def test_parameters_from_json_randomizes_null_seed(tmp_path: Path) -> None:
    """A null seed is replaced with a randomly drawn value in [0, 1e6)."""
    payload = _minimal_raw_parameters() | {"seed": None}
    parameters = core.Parameters.from_json(_write_json(tmp_path / "p.json", payload))
    assert parameters.seed is not None
    assert 0 <= parameters.seed < 1e6


def test_parameters_from_json_applies_defaults(tmp_path: Path) -> None:
    """Optional keys absent from the JSON fall back to dataclass defaults."""
    parameters = core.Parameters.from_json(
        _write_json(tmp_path / "p.json", _minimal_raw_parameters())
    )
    assert parameters.container_wall_thickness == -0.2
    assert parameters.container_piston_slack == 0.0
    assert parameters.gravity_field == (0.0, 0.0, -9.8)
    assert parameters.save_blender_file is True
    assert parameters.quit_on_finish is False


def test_parameters_from_json_rejects_unknown_keys(tmp_path: Path) -> None:
    """Unknown JSON keys must fail loudly so typos do not go silent."""
    payload = _minimal_raw_parameters() | {"definitely_not_a_field": 1}
    with pytest.raises(TypeError):
        core.Parameters.from_json(_write_json(tmp_path / "p.json", payload))


def test_parameters_from_json_rejects_missing_required_key(tmp_path: Path) -> None:
    """Required keys missing from the JSON raise at load time, not mid-simulation."""
    payload = _minimal_raw_parameters()
    del payload["scale"]
    with pytest.raises(TypeError):
        core.Parameters.from_json(_write_json(tmp_path / "p.json", payload))


def test_parameters_gravity_field_round_trips_as_tuple(tmp_path: Path) -> None:
    """A JSON list for gravity_field becomes the tuple field of the same values."""
    payload = _minimal_raw_parameters() | {"gravity_field": [0, 0, -1.0]}
    parameters = core.Parameters.from_json(_write_json(tmp_path / "p.json", payload))
    assert parameters.gravity_field == (0, 0, -1.0)


def test_num_particles_total_is_grid_product() -> None:
    """num_particles_total equals the product of the three grid dimensions."""
    parameters = _parameters()
    assert parameters.num_particles_total == 2 * 3 * 4


def test_num_B_particles_is_zero_when_mass_fraction_B_is_zero() -> None:
    """At zero B-mass fraction no B particles are generated."""
    parameters = _parameters(mass_fraction_B=0.0)
    assert core.num_B_particles(parameters, parameters.num_particles_total) == 0


def test_num_B_particles_approaches_total_when_mass_fraction_B_near_one() -> None:
    """As B-mass fraction tends to 1 every slot becomes a B particle."""
    parameters = _parameters(mass_fraction_B=0.999999)
    assert (
        core.num_B_particles(parameters, parameters.num_particles_total)
        == parameters.num_particles_total
    )


def test_particle_density_picks_per_type_value() -> None:
    """particle_density returns density_A for A and density_B for B."""
    parameters = _parameters(density_A=5.0, density_B=15.0)
    assert core.particle_density(parameters, core.ParticleType.A) == 5.0
    assert core.particle_density(parameters, core.ParticleType.B) == 15.0


def test_particle_dimensions_scales_both_axes() -> None:
    """The scale factor must be applied to both radius and height."""
    parameters = _parameters(scale=2.5, r_A=0.1, thickness_A=0.08)
    radius, height = core.particle_dimensions(parameters, core.ParticleType.A)
    assert isclose(radius, 0.25)
    assert isclose(height, 0.2)


def test_particle_dimensions_picks_per_type() -> None:
    """A and B must read from their own r_*/thickness_* fields, not be swapped."""
    parameters = _parameters(
        scale=1.0, r_A=0.1, r_B=0.05, thickness_A=0.08, thickness_B=0.03
    )
    assert core.particle_dimensions(parameters, core.ParticleType.A) == (0.1, 0.08)
    assert core.particle_dimensions(parameters, core.ParticleType.B) == (0.05, 0.03)


@pytest.mark.parametrize("particle_type", [core.ParticleType.A, core.ParticleType.B])
def test_particle_mass_is_density_times_volume(
    particle_type: core.ParticleType,
) -> None:
    """particle_mass equals density(type) * volume_prism(num_sides, r, h)."""
    parameters = _parameters()
    radius, height = core.particle_dimensions(parameters, particle_type)
    expected = core.particle_density(parameters, particle_type) * core.volume_prism(
        parameters.num_sides, radius, height
    )
    assert isclose(core.particle_mass(parameters, particle_type), expected)


def test_particle_mass_scales_linearly_with_density() -> None:
    """Doubling density_A doubles the mass of an A particle."""
    base = _parameters(density_A=5.0)
    doubled = _parameters(density_A=10.0)
    assert isclose(
        core.particle_mass(doubled, core.ParticleType.A),
        2 * core.particle_mass(base, core.ParticleType.A),
    )


def test_particle_mass_scales_cubically_with_scale() -> None:
    """Doubling parameters.scale multiplies mass by 8 (radius^2 * height)."""
    base = _parameters(scale=1.0)
    doubled = _parameters(scale=2.0)
    assert isclose(
        core.particle_mass(doubled, core.ParticleType.A),
        8 * core.particle_mass(base, core.ParticleType.A),
    )


def test_decide_particle_type_is_A_when_fraction_is_one() -> None:
    """number_fraction_A == 1.0 must always yield A regardless of the draw."""
    rng = random.Random(0)
    for _ in range(50):
        assert core.decide_particle_type(1.0, rng) == core.ParticleType.A


def test_decide_particle_type_is_B_when_fraction_is_zero() -> None:
    """number_fraction_A == 0.0 must always yield B regardless of the draw."""
    rng = random.Random(0)
    for _ in range(50):
        assert core.decide_particle_type(0.0, rng) == core.ParticleType.B


def test_decide_particle_type_distribution_matches_fraction() -> None:
    """Empirical A fraction over 10_000 seeded draws stays within +/-0.02 of target."""
    target = 0.3
    rng = random.Random(20260616)
    draws = 10_000
    a_count = sum(
        core.decide_particle_type(target, rng) == core.ParticleType.A
        for _ in range(draws)
    )
    assert abs(a_count / draws - target) < 0.02


def test_build_packing_spec_places_expected_number_of_particles() -> None:
    """The spec has one particle for each grid point."""
    parameters = _parameters(num_particles_x=2, num_particles_y=2, num_particles_z=3)
    spec = core.build_packing_spec(parameters)
    assert len(spec.particles) == 12


def test_build_packing_spec_centers_particle_grid() -> None:
    """Particle locations are centered in x/y and stacked from half-distance in z."""
    parameters = _parameters(
        num_particles_x=2, num_particles_y=2, num_particles_z=2, distance=1.5
    )
    spec = core.build_packing_spec(parameters)
    assert [particle.location for particle in spec.particles] == [
        (-0.75, -0.75, 0.75),
        (-0.75, -0.75, 2.25),
        (-0.75, 0.75, 0.75),
        (-0.75, 0.75, 2.25),
        (0.75, -0.75, 0.75),
        (0.75, -0.75, 2.25),
        (0.75, 0.75, 0.75),
        (0.75, 0.75, 2.25),
    ]


def test_build_packing_spec_is_deterministic_for_seed() -> None:
    """A fixed seed produces identical particle types and rotations."""
    parameters = _parameters(seed=20260813)
    first = core.build_packing_spec(parameters)
    second = core.build_packing_spec(parameters)
    assert first.particles == second.particles


def test_build_packing_spec_assigns_particle_physics_fields() -> None:
    """Particle specs carry the physics values Blender needs."""
    parameters = _parameters(
        mass_fraction_B=0.0,
        particle_friction=0.2,
        particle_restitution=0.3,
        particle_damping=0.4,
    )
    particle = core.build_packing_spec(parameters).particles[0]
    assert particle.particle_type == core.ParticleType.A
    assert particle.radius == parameters.r_A * parameters.scale
    assert particle.height == parameters.thickness_A * parameters.scale
    assert particle.mass == core.particle_mass(parameters, core.ParticleType.A)
    assert particle.friction == 0.2
    assert particle.restitution == 0.3
    assert particle.damping == 0.4
    assert all(0 <= angle <= 2 * pi for angle in particle.rotation)


def test_build_packing_spec_computes_piston_and_container() -> None:
    """Piston and container dimensions match the existing Blender formulas."""
    parameters = _parameters(
        num_particles_x=2,
        num_particles_z=4,
        distance=1.5,
        container_piston_slack=0.1,
        container_wall_thickness=-0.3,
        use_piston=True,
        mass_piston=7.0,
    )
    spec = core.build_packing_spec(parameters)
    assert spec.piston.enabled is True
    assert spec.piston.side_length == 2.7
    assert spec.piston.z == 8.775
    assert spec.piston.mass == 7.0
    assert spec.container.side_length == 3.0
    assert spec.container.height == 11.137500000000001
    assert spec.container.wall_thickness == -0.3


def test_build_packing_spec_carries_runtime_fields() -> None:
    """Frame range and gravity are available without importing Blender."""
    parameters = _parameters(end_frame=123, gravity_field=(1.0, 2.0, -3.0))
    spec = core.build_packing_spec(parameters)
    assert spec.parameters == parameters
    assert spec.frame_start == 1
    assert spec.frame_end == 123
    assert spec.gravity == (1.0, 2.0, -3.0)


def test_build_packing_spec_can_disable_piston_creation() -> None:
    """The piston spec is still dimensioned when creation is disabled."""
    parameters = _parameters(use_piston=False)
    spec = core.build_packing_spec(parameters)
    assert spec.piston.enabled is False
    assert spec.piston.side_length > 0
    assert spec.piston.z > 0
