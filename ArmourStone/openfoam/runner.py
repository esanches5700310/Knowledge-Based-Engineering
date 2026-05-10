"""
runner.py

Runs the OpenFOAM case using Docker.

This script should be run from WSL / Ubuntu, not from inside Docker.

use:
cd "/mnt/c/Users/estew/Documents/TU Delft/MSc Flight Performance/AE4204 Knowledge Based Engineering/Knowledge-Based-Engineering/ArmourStone"
python3 openfoam/case_generator.py
python3 openfoam/runner.py
python3 openfoam/postprocess.py
"""

import subprocess
from pathlib import Path


DOCKER_IMAGE = "opencfd/openfoam-default:2206"
CASE_NAME = "case_003_slope_jet_bed_slope_2d"

def armourstone_folder():
    """Return the ArmourStone folder."""
    return Path(__file__).resolve().parents[1]


def case_folder():
    """Return the OpenFOAM case folder."""
    return armourstone_folder() / "cases" / CASE_NAME


def run_openfoam():
    """Run blockMesh, checkMesh, simpleFoam and write cell centres."""

    root = armourstone_folder()
    case_dir = case_folder()

    if not case_dir.exists():
        raise FileNotFoundError(
            f"Case folder not found:\n{case_dir}\n\n"
            "Run case_generator.py first."
        )

    # Path of the case inside the Docker container
    docker_case_dir = f"/work/cases/{CASE_NAME}"

    commands_inside_docker = f"""
cd {docker_case_dir}

echo "Running blockMesh..."
blockMesh > log.blockMesh 2>&1

echo "Running checkMesh..."
checkMesh > log.checkMesh 2>&1

echo "Running simpleFoam..."
simpleFoam > log.simpleFoam 2>&1

echo "Writing cell centres..."
postProcess -func writeCellCentres -latestTime > log.writeCellCentres 2>&1 || true

echo "Creating ParaView file..."
touch {CASE_NAME}.foam

echo "Done."
"""

    docker_command = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{root}:/work",
        DOCKER_IMAGE,
        "bash",
        "-lc",
        commands_inside_docker,
    ]

    result = subprocess.run(
        docker_command,
        cwd=root,
        text=True,
        capture_output=True,
    )

    print(result.stdout)

    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError("OpenFOAM run failed. Check the log files.")

    print("OpenFOAM finished successfully.")
    print(f"Case folder: {case_dir}")
    print(f"ParaView file: {case_dir / (CASE_NAME + '.foam')}")


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

    # Useful quick checks
    print_log_tail("log.checkMesh")
    print_log_tail("log.simpleFoam")