"""
cfd_interface.py

Interface between the KBE application and the OpenFOAM workflow.

This file:
1. receives inputs from the ParaPy/KBE model,
2. updates the OpenFOAM case_generator settings,
3. creates the CFD case,
4. runs OpenFOAM through Docker/Ubuntu,
5. postprocesses the result,
6. returns the governing velocity to the KBE app.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import platform
import subprocess
import shlex


@dataclass
class CFDSettings:
    """Container for the OpenFOAM scenario inputs."""

    case_name: str = "case_kbe_2d"

    # Geometry
    water_depth: float = 5.0
    flat_bed_length: float = 30.0
    slope_angle_deg: float = 30.0
    slope_top_fraction: float = 1.0
    domain_width: float = 0.1

    # Propeller / actuator source
    propeller_distance_to_slope_toe: float = 10.0
    propeller_center_z: float = 1.2
    propeller_diameter: float = 0.8
    propeller_zone_length: float = 0.8
    jet_velocity: float = 3.0

    # Fluid
    kinematic_viscosity: float = 1.0e-6

    # Mesh
    cells_flat_x: int = 240
    cells_slope_x: int = 80
    cells_z: int = 80

    # Postprocessing
    near_wall_height: float = 0.10


def armourstone_folder():
    """Return the ArmourStone folder."""
    return Path(__file__).resolve().parents[1]


def save_cfd_settings(settings):
    """Save the settings used for this CFD run."""
    output_dir = armourstone_folder() / "output" / "cfd_settings"
    output_dir.mkdir(parents=True, exist_ok=True)

    path = output_dir / f"{settings.case_name}_settings.json"
    path.write_text(json.dumps(asdict(settings), indent=4))

    return path


def make_cfd_settings_from_kbe(ship, waterway, jet_velocity, upstream_length=20.0):
    """Create CFD settings from the ParaPy/KBE objects.

    Important:
    waterway.d_slope is interpreted as the distance from the propeller
    to the slope toe.

    The CFD flat bed length is therefore:
    upstream_length + distance from propeller to slope toe

    This keeps enough space upstream of the propeller for recirculation.
    """

    flat_bed_length = upstream_length + waterway.d_slope

    settings = CFDSettings(
        case_name="case_kbe_2d",

        water_depth=waterway.h,
        flat_bed_length=flat_bed_length,
        slope_angle_deg=waterway.beta,
        slope_top_fraction=1.0,
        domain_width=0.1,

        propeller_distance_to_slope_toe=waterway.d_slope,
        propeller_center_z=ship.Z_p,
        propeller_diameter=ship.D_p,
        propeller_zone_length=0.8,
        jet_velocity=jet_velocity,

        kinematic_viscosity=1.0e-6,

        cells_flat_x=240,
        cells_slope_x=80,
        cells_z=80,

        near_wall_height=0.10,
    )

    return settings


def apply_settings_to_case_generator(settings):
    """Apply CFDSettings to the existing case_generator.py module."""

    from openfoam import case_generator

    case_generator.CASE_NAME = settings.case_name
    case_generator.TEMPLATE_NAME = "slope_jet_bed_slope_large_2d"

    case_generator.WATER_DEPTH = settings.water_depth
    case_generator.FLAT_BED_LENGTH = settings.flat_bed_length
    case_generator.SLOPE_ANGLE_DEG = settings.slope_angle_deg
    case_generator.SLOPE_TOP_FRACTION = settings.slope_top_fraction
    case_generator.DOMAIN_WIDTH = settings.domain_width

    case_generator.PROPELLER_DISTANCE_TO_SLOPE_TOE = settings.propeller_distance_to_slope_toe
    case_generator.PROPELLER_CENTER_Z = settings.propeller_center_z
    case_generator.PROPELLER_DIAMETER = settings.propeller_diameter
    case_generator.PROPELLER_ZONE_LENGTH = settings.propeller_zone_length
    case_generator.JET_VELOCITY = settings.jet_velocity

    case_generator.KINEMATIC_VISCOSITY = settings.kinematic_viscosity

    case_generator.CELLS_FLAT_X = settings.cells_flat_x
    case_generator.CELLS_SLOPE_X = settings.cells_slope_x
    case_generator.CELLS_Z = settings.cells_z

    case_generator.NEAR_WALL_HEIGHT = settings.near_wall_height

    return case_generator


def run_openfoam_workflow(settings):
    """Run the complete OpenFOAM workflow and return the CFD summary."""

    save_cfd_settings(settings)

    case_generator = apply_settings_to_case_generator(settings)
    case_generator.create_case()

    if platform.system() == "Windows":
        run_openfoam_runner_in_wsl(settings.case_name)
    else:
        from openfoam import runner
        runner.CASE_NAME = settings.case_name
        runner.run_openfoam()

    from openfoam import postprocess
    postprocess.CASE_NAME = settings.case_name
    summary = postprocess.extract_results()

    return summary


def get_governing_velocity(settings):
    """Run CFD and return only the governing velocity."""
    summary = run_openfoam_workflow(settings)
    return summary["governing_velocity"]


def windows_path_to_wsl_path(path):
    """Convert a Windows path to a WSL path.

    Example:
    C:\\Users\\... becomes /mnt/c/Users/...
    """

    result = subprocess.run(
        ["wsl", "wslpath", "-a", str(path)],
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Could not convert Windows path to WSL path.\n"
            f"Path: {path}\n"
            f"Error:\n{result.stderr}"
        )

    return result.stdout.strip()


def run_openfoam_runner_in_wsl(case_name):
    """Run openfoam/runner.py inside WSL from a Windows Python process."""

    root_windows = armourstone_folder()
    root_wsl = windows_path_to_wsl_path(root_windows)

    command = (
        f"cd {shlex.quote(root_wsl)} && "
        f"python3 openfoam/runner.py {shlex.quote(case_name)}"
    )

    print("Running OpenFOAM in WSL:")
    print(command)

    result = subprocess.run(
        ["wsl", "bash", "-lc", command],
        text=True,
        capture_output=True,
    )

    print(result.stdout)

    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError("OpenFOAM run in WSL failed.")