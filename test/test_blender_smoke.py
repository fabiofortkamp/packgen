"""Optional smoke test for the Blender runtime adapter."""

import json
import os
import subprocess
from pathlib import Path

import pytest

import packgen


@pytest.mark.blender
@pytest.mark.slow
@pytest.mark.skipif(
    os.environ.get("PACKGEN_RUN_BLENDER_TESTS") != "1",
    reason="set PACKGEN_RUN_BLENDER_TESTS=1 to run the Blender smoke test",
)
def test_blender_adapter_writes_json_for_tiny_simulation(tmp_path: Path) -> None:
    """Run the Blender adapter only when explicitly requested."""
    parameters = {
        "scale": 1.0,
        "r_A": 0.1,
        "r_B": 0.05,
        "thickness_A": 0.08,
        "thickness_B": 0.03,
        "density_A": 5.0,
        "density_B": 15.0,
        "num_sides": 6,
        "num_particles_x": 1,
        "num_particles_y": 1,
        "num_particles_z": 1,
        "distance": 1.5,
        "mass_fraction_B": 0.0,
        "particle_friction": 0.8,
        "particle_restitution": 0.5,
        "particle_damping": 0.8,
        "mass_piston": 1.0,
        "end_frame": 1,
        "use_piston": False,
        "seed": 42,
        "save_blender_file": False,
        "save_json_file": True,
        "save_stl_file": False,
        "quit_on_finish": True,
    }
    parameter_file = tmp_path / "tiny.json"
    parameter_file.write_text(json.dumps(parameters))

    result = subprocess.run(
        [
            packgen.find_Blender_executable(),
            "--background",
            "-P",
            str(packgen.BLENDER_SCRIPT),
            "--",
            str(parameter_file),
        ],
        check=False,
        cwd=tmp_path,
    )

    assert result.returncode == 0
    assert (tmp_path / "packing_tiny.json").exists()
