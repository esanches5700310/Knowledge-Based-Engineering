"""
runner_3D.py

Runs the 3D OpenFOAM case using Docker.

Run from WSL/Ubuntu, not inside Docker.

Use:
cd "/mnt/c/Users/estew/Documents/TU Delft/MSc Flight Performance/AE4204 Knowledge Based Engineering/Knowledge-Based-Engineering/ArmourStone"
python3 openfoam/case_generator_3D.py
python3 openfoam/runner_3D.py
python3 openfoam/postprocess_3D.py
"""

import os
import sys
import subprocess
from pathlib import Path


DOCKER_IMAGE = "opencfd/openfoam-default:2206"
DEFAULT_CASE_NAME = "case_005_slope_jet_bed_slope_large_3d"


if len(sys.argv) > 1:
    CASE_NAME = sys.argv[1]
else:
    CASE_NAME = os.environ.get("OPENFOAM_CASE_NAME", DEFAULT_CASE_NAME)


def armourstone_folder():
    """Return the ArmourStone folder."""
    return Path(__file__).resolve().parents[1]


def case_folder():
    """Return the 3D OpenFOAM case folder."""
    return armourstone_folder() / "cases" / CASE_NAME


def write_run_script():
    """Write a small shell script that will be executed inside Docker."""

    case_dir = case_folder()

    script_text = f"""#!/bin/bash

source /usr/lib/openfoam/openfoam2206/etc/bashrc

set -e

cd /work/cases/{CASE_NAME}

echo "Running blockMesh..."
blockMesh > log.blockMesh 2>&1

echo "Running checkMesh..."
checkMesh > log.checkMesh 2>&1

echo "Running topoSet..."
topoSet > log.topoSet 2>&1

echo "Running simpleFoam..."
simpleFoam > log.simpleFoam 2>&1

echo "Writing cell centres..."
postProcess -func writeCellCentres -latestTime > log.writeCellCentres 2>&1 || true

echo "Creating ParaView file..."
touch {CASE_NAME}.foam

echo "Done."
"""

    script_path = case_dir / "run_openfoam.sh"
    script_path.write_text(script_text)
    script_path.chmod(0o755)

    return script_path


def run_openfoam():
    """Run the OpenFOAM commands inside the Docker container."""

    root = armourstone_folder()
    case_dir = case_folder()

    if not case_dir.exists():
        raise FileNotFoundError(
            f"Case folder not found:\n{case_dir}\n\n"
            "Run case_generator_3D.py first."
        )

    write_run_script()

    docker_script_path = f"/work/cases/{CASE_NAME}/run_openfoam.sh"

    docker_command = [
        "docker",
        "run",
        "--rm",
        "--entrypoint",
        "/bin/bash",
        "-v",
        f"{root}:/work",
        DOCKER_IMAGE,
        docker_script_path,
    ]

    print("Running Docker command:")
    print(" ".join(docker_command))
    print()

    result = subprocess.run(
        docker_command,
        cwd=root,
        text=True,
        capture_output=True,
    )

    print(result.stdout)

    if result.returncode != 0:
        print(result.stderr)
        print_log_tail("log.blockMesh", 80)
        print_log_tail("log.checkMesh", 80)
        print_log_tail("log.topoSet", 80)
        print_log_tail("log.simpleFoam", 120)
        raise RuntimeError("3D OpenFOAM run failed. Check the log files.")

    print("3D OpenFOAM finished.")
    print(f"Case folder: {case_dir}")
    print(f"ParaView file: {case_dir / (CASE_NAME + '.foam')}")

    print_log_tail("log.checkMesh", 40)
    print_log_tail("log.topoSet", 40)
    print_log_tail("log.simpleFoam", 80)


def print_log_tail(log_name, n_lines=40):
    """Print the last lines of a log file."""

    path = case_folder() / log_name

    if not path.exists():
        print(f"Log file not found: {path}")
        return

    lines = path.read_text(errors="ignore").splitlines()

    print(f"\n--- Last {n_lines} lines of {log_name} ---")
    for line in lines[-n_lines:]:
        print(line)


if __name__ == "__main__":
    run_openfoam()