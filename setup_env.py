#!/usr/bin/env python3
"""
setup_env.py - Virtual Environment Stabilizer (TRD v2.0 Production)

Enforces a stable virtual environment running Python 3.11 or 3.12 before the
CrewAI pipeline is executed. This bypasses the Python 3.14 wheel-compilation
failures that break langchain-core / CrewAI 0.11.2.

Usage:
    python setup_env.py          # create/validate venv + install deps
    python setup_env.py --check  # only validate the environment
"""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
VENV_DIR = PROJECT_ROOT / ".venv"
REQUIREMENTS = PROJECT_ROOT / "requirements.txt"
ACCEPTED_MAJOR_MINOR = {"3.11", "3.12"}


def log(msg: str) -> None:
    print(f"[setup_env] {msg}")


def detect_python() -> str | None:
    """Return the path to a usable Python 3.11/3.12 interpreter, or None."""
    candidates = [
        sys.executable,
        "python3.12", "python3.11",
        "python3", "python",
    ]
    seen = set()
    for cand in candidates:
        if cand in seen:
            continue
        seen.add(cand)
        try:
            result = subprocess.run(
                [cand, "--version"],
                capture_output=True, text=True, timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if result.returncode != 0:
            continue
        version = result.stdout.strip() or result.stderr.strip()
        # version looks like "Python 3.12.4"
        for token in version.split():
            if token.startswith("Python"):
                continue
            parts = token.split(".")
            if len(parts) >= 2:
                key = f"{parts[0]}.{parts[1]}"
                if key in ACCEPTED_MAJOR_MINOR:
                    return cand
    return None


def ensure_venv(python_exe: str) -> None:
    if VENV_DIR.exists():
        log(f"Virtual environment already exists at {VENV_DIR}")
        return
    log(f"Creating virtual environment with {python_exe} ...")
    subprocess.run(
        [python_exe, "-m", "venv", str(VENV_DIR)],
        check=True,
    )
    log("Virtual environment created.")


def venv_python() -> str:
    if os.name == "nt":
        return str(VENV_DIR / "Scripts" / "python.exe")
    return str(VENV_DIR / "bin" / "python")


def install_dependencies(py_exe: str) -> None:
    log("Upgrading pip ...")
    subprocess.run([py_exe, "-m", "pip", "install", "--upgrade", "pip"], check=False)
    if not REQUIREMENTS.exists():
        log(f"requirements.txt not found at {REQUIREMENTS}; skipping install.")
        return
    log(f"Installing dependencies from {REQUIREMENTS} ...")
    subprocess.run(
        [py_exe, "-m", "pip", "install", "-r", str(REQUIREMENTS)],
        check=True,
    )
    log("Dependencies installed.")


def main(check_only: bool = False) -> int:
    log(f"Project root: {PROJECT_ROOT}")
    py = detect_python()
    if not py:
        log("ERROR: No Python 3.11 or 3.12 interpreter found on PATH.")
        log("       Install Python 3.11 or 3.12 and re-run this script.")
        return 1
    log(f"Using Python interpreter: {py}")

    if check_only:
        log("Environment check passed.")
        return 0

    ensure_venv(py)
    install_dependencies(venv_python())
    log("Setup complete. Activate the venv and run: python main.py")
    return 0


if __name__ == "__main__":
    check_only = "--check" in sys.argv
    raise SystemExit(main(check_only=check_only))
