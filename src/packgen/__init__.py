import os.path
import platform
import subprocess
from pathlib import Path

PROJECT_PATH = Path(__file__).parent
BLENDER_SCRIPT = PROJECT_PATH / "blend.py"
BLENDER_SCRIPT_FLAG = "-P"


def find_Blender_executable() -> str:
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
    executable = find_Blender_executable()
    args = [executable, BLENDER_SCRIPT_FLAG, str(BLENDER_SCRIPT)]
    _ = subprocess.run(args)
