"""packgen - A particle packing generator.

`packgen` simulates the process of placing prismatic particles
above a container, and letting gravity, collisions, and friction
act on them, until they settle into a stable configuration inside
the container.

The current physics engine is based on Blender.
"""

import os.path
import platform
import subprocess
import sys
from pathlib import Path

PROJECT_PATH = Path(__file__).parent
BLENDER_SCRIPT = PROJECT_PATH / "blend.py"
BLENDER_SCRIPT_FLAG = "-P"


def find_Blender_executable() -> str:
    """Find the Blender executable path based on the platform.

    Currently supports Windows and macOS.
    """
    platform_name = platform.system()
    if platform_name == "Windows":
        return os.path.join(
            "C:",
            "Program Files",
            "Blender Foundation",
            "Blender",
            "4.3",
            "Blender.exe",
        )
    elif platform_name == "Darwin":
        return os.path.join(
            "/Applications", "Blender.app", "Contents", "MacOS", "Blender"
        )
    else:
        raise NotImplementedError


def main() -> None:
    """Main entry point for the packgen script.

    This function calls the Blender executable, passing
    the driver script and any additional command-line arguments.
    """  # noqa: D401
    executable = find_Blender_executable()
    cmd_args = []
    if "--" in sys.argv:
        cmd_args = sys.argv[sys.argv.index("--") :]  # get all args after "--"
    args = [executable, BLENDER_SCRIPT_FLAG, str(BLENDER_SCRIPT)] + cmd_args
    _ = subprocess.run(args)
