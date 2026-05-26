"""Custom setuptools setup.py that builds the React frontend before packaging.

The setuptools legacy backend (used in pyproject.toml) automatically picks up
this file and merges it with pyproject.toml configuration.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist


class BuildPyWithFrontend(build_py):
    """Extend build_py to compile the React frontend before packaging."""

    def run(self) -> None:
        _build_frontend()
        super().run()


class SdistWithFrontend(sdist):
    """Extend sdist to compile the React frontend before creating the source distribution."""

    def run(self) -> None:
        _build_frontend()
        super().run()


def _build_frontend() -> None:
    root = Path(__file__).parent
    web_dir = root / "web"           # source: <repo>/web/
    dest_dist = root / "webui" / "web" / "dist"  # target: inside the Python package

    # Pre-built by CI (copied before python -m build runs in isolated env)
    if dest_dist.exists() and any(dest_dist.iterdir()):
        print(f"[setup] Frontend dist already present at {dest_dist}, skipping build ✓", file=sys.stderr)
        return

    if not web_dir.exists():
        print("[setup] web/ directory not found, skipping frontend build", file=sys.stderr)
        return

    bun = shutil.which("bun") or shutil.which("npm")
    if bun is None:
        print(
            "[setup] WARNING: neither 'bun' nor 'npm' found — "
            "frontend will NOT be embedded in the wheel.\n"
            "Run 'bun run build' inside web/ manually, then copy dist/ to webui/web/dist/.",
            file=sys.stderr,
        )
        return

    print(f"[setup] Building frontend with {bun} …", file=sys.stderr)
    result = subprocess.run([bun, "run", "build"], cwd=str(web_dir), check=False)
    if result.returncode != 0:
        print("[setup] Frontend build FAILED — wheel created without static assets", file=sys.stderr)
        return

    # Copy dist output into the Python package so setuptools picks it up
    src_dist = web_dir / "dist"
    if src_dist.exists() and src_dist != dest_dist:
        if dest_dist.exists():
            shutil.rmtree(dest_dist)
        shutil.copytree(src_dist, dest_dist)
        print(f"[setup] Frontend dist copied to {dest_dist} ✓", file=sys.stderr)
    else:
        print("[setup] Frontend build OK ✓", file=sys.stderr)


setup(cmdclass={"build_py": BuildPyWithFrontend, "sdist": SdistWithFrontend})
