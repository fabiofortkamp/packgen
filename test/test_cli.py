"""Tests for the host-Python launcher."""

import subprocess

import pytest

import packgen


def test_find_blender_executable_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    """Windows uses the conventional Blender installation path."""
    monkeypatch.setattr(packgen.platform, "system", lambda: "Windows")

    assert packgen.find_Blender_executable() == (
        "C:/Program Files/Blender Foundation/Blender/4.3/Blender.exe"
    )


def test_find_blender_executable_on_macos(monkeypatch: pytest.MonkeyPatch) -> None:
    """MacOS uses the application bundle executable."""
    monkeypatch.setattr(packgen.platform, "system", lambda: "Darwin")

    assert packgen.find_Blender_executable() == (
        "/Applications/Blender.app/Contents/MacOS/Blender"
    )


def test_find_blender_executable_on_linux_prefers_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Linux uses PATH when a blender executable exists there."""
    monkeypatch.setattr(packgen.platform, "system", lambda: "Linux")
    monkeypatch.setattr(packgen.shutil, "which", lambda name: f"/usr/local/bin/{name}")

    assert packgen.find_Blender_executable() == "/usr/local/bin/blender"


def test_find_blender_executable_on_linux_falls_back_to_bin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Linux falls back to /bin/blender when PATH lookup fails."""
    monkeypatch.setattr(packgen.platform, "system", lambda: "Linux")
    monkeypatch.setattr(packgen.shutil, "which", lambda _name: None)

    assert packgen.find_Blender_executable() == "/bin/blender"


def test_find_blender_executable_rejects_unknown_platform(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unsupported platforms fail before subprocess launch."""
    monkeypatch.setattr(packgen.platform, "system", lambda: "Plan9")

    with pytest.raises(NotImplementedError):
        packgen.find_Blender_executable()


def test_main_launches_blender_with_forwarded_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The console script forwards the driver script and args after --."""
    calls: list[list[str]] = []
    monkeypatch.setattr(packgen, "find_Blender_executable", lambda: "Blender")
    monkeypatch.setattr(packgen.sys, "argv", ["packgen", "--", "params.json"])

    def fake_run(
        args: list[str], *, check: bool
    ) -> subprocess.CompletedProcess[str]:
        assert check is False
        calls.append(args)
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(packgen.subprocess, "run", fake_run)

    packgen.main()

    assert calls == [
        ["Blender", "-P", str(packgen.BLENDER_SCRIPT), "--", "params.json"]
    ]


def test_main_launches_blender_without_parameter_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The console script lets the Blender script use its default parameter file."""
    calls: list[list[str]] = []
    monkeypatch.setattr(packgen, "find_Blender_executable", lambda: "Blender")
    monkeypatch.setattr(packgen.sys, "argv", ["packgen"])

    def fake_run(
        args: list[str], *, check: bool
    ) -> subprocess.CompletedProcess[str]:
        assert check is False
        calls.append(args)
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(packgen.subprocess, "run", fake_run)

    packgen.main()

    assert calls == [["Blender", "-P", str(packgen.BLENDER_SCRIPT)]]
