"""Tests for the volumetric calculations and parameter loading."""

import importlib
import json
import os
import random
from math import isclose, sqrt
from pathlib import Path

import pytest

from packgen import blend


def test_blend_module_imports_without_parameters_file(tmp_path: Path) -> None:
    """Importing packgen.blend must not require a parameters.json in cwd."""
    original_cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        importlib.reload(blend)
    finally:
        os.chdir(original_cwd)


def test_volume_prism_coincides_with_hexagon() -> None:
    """Check volume calculation with known expression for hexagonal prisms."""
    r = 2.3
    h = 4.5
    V_actual = blend.volume_prism(6, r, h)

    # use expression for hexagonal prisms that are used of other parts of our codebase
    area_hexagon = 3 * sqrt(3) / 2 * r**2
    V_expected = area_hexagon * h
    assert isclose(V_expected, V_actual)


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


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload))
    return path


def test_parameters_from_json_preserves_seed(tmp_path: Path) -> None:
    """A numeric seed in the JSON is loaded verbatim."""
    payload = _minimal_raw_parameters() | {"seed": 12345}
    p = blend.Parameters.from_json(_write_json(tmp_path / "p.json", payload))
    assert p.seed == 12345


def test_parameters_from_json_randomizes_null_seed(tmp_path: Path) -> None:
    """A null seed is replaced with a randomly drawn value in [0, 1e6)."""
    payload = _minimal_raw_parameters() | {"seed": None}
    p = blend.Parameters.from_json(_write_json(tmp_path / "p.json", payload))
    assert p.seed is not None
    assert 0 <= p.seed < 1e6


def test_parameters_from_json_applies_defaults(tmp_path: Path) -> None:
    """Optional keys absent from the JSON fall back to dataclass defaults."""
    p = blend.Parameters.from_json(
        _write_json(tmp_path / "p.json", _minimal_raw_parameters())
    )
    assert p.container_wall_thickness == -0.2
    assert p.container_piston_slack == 0.0
    assert p.gravity_field == (0.0, 0.0, -9.8)
    assert p.save_blender_file is True
    assert p.quit_on_finish is False


def test_parameters_from_json_rejects_unknown_keys(tmp_path: Path) -> None:
    """Unknown JSON keys must fail loudly so typos do not go silent."""
    payload = _minimal_raw_parameters() | {"definitely_not_a_field": 1}
    with pytest.raises(TypeError):
        blend.Parameters.from_json(_write_json(tmp_path / "p.json", payload))


def test_parameters_from_json_rejects_missing_required_key(tmp_path: Path) -> None:
    """Required keys missing from the JSON raise at load time, not mid-simulation."""
    payload = _minimal_raw_parameters()
    del payload["scale"]
    with pytest.raises(TypeError):
        blend.Parameters.from_json(_write_json(tmp_path / "p.json", payload))


def test_parameters_gravity_field_round_trips_as_list(tmp_path: Path) -> None:
    """A JSON list for gravity_field becomes the tuple field of the same values."""
    payload = _minimal_raw_parameters() | {"gravity_field": [0, 0, -1.0]}
    p = blend.Parameters.from_json(_write_json(tmp_path / "p.json", payload))
    assert p.gravity_field == (0, 0, -1.0)


def test_num_particles_total_is_grid_product() -> None:
    """num_particles_total equals the product of the three grid dimensions."""
    p = blend.Parameters(**_minimal_raw_parameters())  # type: ignore[arg-type]
    assert p.num_particles_total == 2 * 3 * 4


def test_num_B_particles_is_zero_when_mass_fraction_B_is_zero() -> None:
    """At zero B-mass fraction no B particles are generated."""
    p = blend.Parameters(
        **(_minimal_raw_parameters() | {"mass_fraction_B": 0.0})  # type: ignore[arg-type]
    )
    assert blend.num_B_particles(p, p.num_particles_total) == 0


def test_num_B_particles_approaches_total_when_mass_fraction_B_near_one() -> None:
    """As B-mass fraction tends to 1 every slot becomes a B particle."""
    p = blend.Parameters(
        **(_minimal_raw_parameters() | {"mass_fraction_B": 0.999999})  # type: ignore[arg-type]
    )
    assert blend.num_B_particles(p, p.num_particles_total) == p.num_particles_total


def _parameters(**overrides: object) -> blend.Parameters:
    return blend.Parameters(**(_minimal_raw_parameters() | overrides))  # type: ignore[arg-type]


def test_particle_density_picks_per_type_value() -> None:
    """particle_density returns density_A for A and density_B for B."""
    p = _parameters(density_A=5.0, density_B=15.0)
    assert blend.particle_density(p, blend.ParticleType.A) == 5.0
    assert blend.particle_density(p, blend.ParticleType.B) == 15.0


def test_particle_dimensions_scales_both_axes() -> None:
    """The scale factor must be applied to both radius and height."""
    p = _parameters(scale=2.5, r_A=0.1, thickness_A=0.08)
    radius, height = blend.particle_dimensions(p, blend.ParticleType.A)
    assert isclose(radius, 0.25)
    assert isclose(height, 0.2)


def test_particle_dimensions_picks_per_type() -> None:
    """A and B must read from their own r_*/thickness_* fields, not be swapped."""
    p = _parameters(
        scale=1.0, r_A=0.1, r_B=0.05, thickness_A=0.08, thickness_B=0.03
    )
    assert blend.particle_dimensions(p, blend.ParticleType.A) == (0.1, 0.08)
    assert blend.particle_dimensions(p, blend.ParticleType.B) == (0.05, 0.03)


@pytest.mark.parametrize("particle_type", [blend.ParticleType.A, blend.ParticleType.B])
def test_particle_mass_is_density_times_volume(
    particle_type: blend.ParticleType,
) -> None:
    """particle_mass equals density(type) * volume_prism(num_sides, r, h)."""
    p = _parameters()
    radius, height = blend.particle_dimensions(p, particle_type)
    expected = blend.particle_density(p, particle_type) * blend.volume_prism(
        p.num_sides, radius, height
    )
    assert isclose(blend.particle_mass(p, particle_type), expected)


def test_particle_mass_scales_linearly_with_density() -> None:
    """Doubling density_A doubles the mass of an A particle."""
    base = _parameters(density_A=5.0)
    doubled = _parameters(density_A=10.0)
    assert isclose(
        blend.particle_mass(doubled, blend.ParticleType.A),
        2 * blend.particle_mass(base, blend.ParticleType.A),
    )


def test_particle_mass_scales_cubically_with_scale() -> None:
    """Doubling parameters.scale multiplies mass by 8 (radius^2 * height)."""
    base = _parameters(scale=1.0)
    doubled = _parameters(scale=2.0)
    assert isclose(
        blend.particle_mass(doubled, blend.ParticleType.A),
        8 * blend.particle_mass(base, blend.ParticleType.A),
    )


def test_decide_particle_type_is_A_when_fraction_is_one() -> None:
    """number_fraction_A == 1.0 must always yield A regardless of the draw."""
    random.seed(0)
    for _ in range(50):
        assert blend.decide_particle_type(1.0) == blend.ParticleType.A


def test_decide_particle_type_is_B_when_fraction_is_zero() -> None:
    """number_fraction_A == 0.0 must always yield B regardless of the draw."""
    random.seed(0)
    for _ in range(50):
        assert blend.decide_particle_type(0.0) == blend.ParticleType.B


def test_decide_particle_type_distribution_matches_fraction() -> None:
    """Empirical A fraction over 10_000 seeded draws stays within ±0.02 of target."""
    target = 0.3
    random.seed(20260616)
    draws = 10_000
    a_count = sum(
        blend.decide_particle_type(target) == blend.ParticleType.A
        for _ in range(draws)
    )
    assert abs(a_count / draws - target) < 0.02


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
