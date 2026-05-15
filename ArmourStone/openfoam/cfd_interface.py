"""
cfd_interface.py

Interface between the KBE application and the OpenFOAM workflow.

This file:
1. receives inputs from the ParaPy/KBE model,
2. chooses between the 2D and 3D OpenFOAM setup,
3. creates the CFD case,
4. runs OpenFOAM through Docker/WSL,
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

    # General
    simulation_type: str = "2D"       # "2D" or "3D"
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
    cells_y: int = 1
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


def check_simulation_type(simulation_type):
    """Check whether the selected OpenFOAM simulation type is valid."""
    simulation_type = simulation_type.upper()

    if simulation_type not in ["2D", "3D"]:
        raise ValueError(
            "openfoam_simulation_type must be either '2D' or '3D'. "
            f"Received: {simulation_type}"
        )

    return simulation_type

def make_cfd_settings_from_kbe(
            ship,
            waterway,
            jet_velocity,
            simulation_type="2D",
            propeller_to_slope_distance=20.0,
            left_boundary_to_propeller_2d=20.0,
            left_boundary_to_propeller_3d=5.0,
            domain_width_3d=12.0,
            cells_flat_x_2d=240,
            cells_slope_x_2d=80,
            cells_z_2d=80,
            cells_flat_x_3d=180,
            cells_slope_x_3d=60,
            cells_y_3d=36,
            cells_z_3d=50,
    ):
    """Create CFD settings from the ParaPy/KBE objects.

    waterway.d_slope is interpreted as the distance from the propeller
    to the slope toe.

    For both 2D and 3D:
    flat_bed_length = upstream_length + propeller-to-slope distance

    The difference is that the 2D case needs a larger upstream length
    because the return flow is constrained in the x-z plane. The 3D case
    can use a shorter upstream length because lateral spreading in y is
    possible.
    """

    simulation_type = check_simulation_type(simulation_type)

    if simulation_type == "2D":
        left_boundary_to_propeller = left_boundary_to_propeller_2d
        case_name = "case_kbe_2d"
        domain_width = 0.1

        cells_flat_x = cells_flat_x_2d
        cells_slope_x = cells_slope_x_2d
        cells_y = 1
        cells_z = cells_z_2d

    elif simulation_type == "3D":
        left_boundary_to_propeller = left_boundary_to_propeller_3d
        case_name = "case_kbe_3d"
        domain_width = domain_width_3d

        cells_flat_x = cells_flat_x_3d
        cells_slope_x = cells_slope_x_3d
        cells_y = cells_y_3d
        cells_z = cells_z_3d

    else:
        raise ValueError(f"Unsupported simulation type: {simulation_type}")

    flat_bed_length = left_boundary_to_propeller + propeller_to_slope_distance

    settings = CFDSettings(
        simulation_type=simulation_type,
        case_name=case_name,

        water_depth=waterway.h,
        flat_bed_length=flat_bed_length,
        slope_angle_deg=waterway.beta,
        slope_top_fraction=1.0,
        domain_width=domain_width,

        propeller_distance_to_slope_toe=propeller_to_slope_distance,
        propeller_center_z=ship.Z_p,
        propeller_diameter=ship.D_p,
        propeller_zone_length=0.8,
        jet_velocity=jet_velocity,

        kinematic_viscosity=1.0e-6,

        cells_flat_x=cells_flat_x,
        cells_slope_x=cells_slope_x,
        cells_y=cells_y,
        cells_z=cells_z,

        near_wall_height=0.10,
    )

    return settings


def apply_settings_to_2d_case_generator(settings):
    """Apply CFDSettings to the 2D case generator."""

    from openfoam import case_generator

    case_generator.CASE_NAME = settings.case_name
    case_generator.TEMPLATE_NAME = "slope_jet_bed_slope_large_2d"

    case_generator.WATER_DEPTH = settings.water_depth
    case_generator.FLAT_BED_LENGTH = settings.flat_bed_length
    case_generator.SLOPE_ANGLE_DEG = settings.slope_angle_deg
    case_generator.SLOPE_TOP_FRACTION = settings.slope_top_fraction
    case_generator.DOMAIN_WIDTH = settings.domain_width

    case_generator.PROPELLER_DISTANCE_TO_SLOPE_TOE = (
        settings.propeller_distance_to_slope_toe
    )
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


def apply_settings_to_3d_case_generator(settings):
    """Apply CFDSettings to the 3D case generator."""

    from openfoam import case_generator_3D

    case_generator_3D.CASE_NAME = settings.case_name
    case_generator_3D.TEMPLATE_NAME = "slope_jet_bed_slope_large_3d"

    case_generator_3D.WATER_DEPTH = settings.water_depth
    case_generator_3D.FLAT_BED_LENGTH = settings.flat_bed_length
    case_generator_3D.SLOPE_ANGLE_DEG = settings.slope_angle_deg
    case_generator_3D.SLOPE_TOP_FRACTION = settings.slope_top_fraction
    case_generator_3D.DOMAIN_WIDTH = settings.domain_width

    case_generator_3D.PROPELLER_DISTANCE_TO_SLOPE_TOE = (
        settings.propeller_distance_to_slope_toe
    )
    case_generator_3D.PROPELLER_CENTER_Y = settings.domain_width / 2.0
    case_generator_3D.PROPELLER_CENTER_Z = settings.propeller_center_z
    case_generator_3D.PROPELLER_DIAMETER = settings.propeller_diameter
    case_generator_3D.PROPELLER_ZONE_LENGTH = settings.propeller_zone_length
    case_generator_3D.JET_VELOCITY = settings.jet_velocity

    case_generator_3D.KINEMATIC_VISCOSITY = settings.kinematic_viscosity

    case_generator_3D.CELLS_FLAT_X = settings.cells_flat_x
    case_generator_3D.CELLS_SLOPE_X = settings.cells_slope_x
    case_generator_3D.CELLS_Y = settings.cells_y
    case_generator_3D.CELLS_Z = settings.cells_z

    case_generator_3D.NEAR_WALL_HEIGHT = settings.near_wall_height

    return case_generator_3D


def create_openfoam_case(settings):
    """Create either the 2D or 3D OpenFOAM case."""

    if settings.simulation_type == "2D":
        case_generator = apply_settings_to_2d_case_generator(settings)

    elif settings.simulation_type == "3D":
        case_generator = apply_settings_to_3d_case_generator(settings)

    else:
        raise ValueError(f"Unsupported simulation type: {settings.simulation_type}")

    return case_generator.create_case()


def run_openfoam_workflow(settings):
    """Run the complete OpenFOAM workflow and return the CFD summary."""

    settings.simulation_type = check_simulation_type(settings.simulation_type)

    save_cfd_settings(settings)
    create_openfoam_case(settings)

    if platform.system() == "Windows":
        run_openfoam_runner_in_wsl(
            case_name=settings.case_name,
            simulation_type=settings.simulation_type,
        )
    else:
        run_openfoam_runner_locally(settings)

    summary = postprocess_results(settings)

    return summary


def run_openfoam_runner_locally(settings):
    """Run the correct OpenFOAM runner directly from Linux/WSL."""

    if settings.simulation_type == "2D":
        from openfoam import runner
        runner.CASE_NAME = settings.case_name
        runner.run_openfoam()

    elif settings.simulation_type == "3D":
        from openfoam import runner_3D
        runner_3D.CASE_NAME = settings.case_name
        runner_3D.run_openfoam()

    else:
        raise ValueError(f"Unsupported simulation type: {settings.simulation_type}")


def postprocess_results(settings):
    """Run the correct postprocessor and return the summary dictionary."""

    if settings.simulation_type == "2D":
        from openfoam import postprocess
        postprocess.CASE_NAME = settings.case_name
        return postprocess.extract_results()

    elif settings.simulation_type == "3D":
        from openfoam import postprocess_3D
        postprocess_3D.CASE_NAME = settings.case_name
        return postprocess_3D.extract_results()

    else:
        raise ValueError(f"Unsupported simulation type: {settings.simulation_type}")


def get_governing_velocity(settings):
    """Run CFD and return only the governing velocity."""
    summary = run_openfoam_workflow(settings)
    return summary["governing_velocity"]


def windows_path_to_wsl_path(path):
    """Convert a Windows path to a WSL path."""
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


def run_openfoam_runner_in_wsl(case_name, simulation_type):
    """Run the correct OpenFOAM runner inside WSL from Windows Python."""

    simulation_type = check_simulation_type(simulation_type)

    root_windows = armourstone_folder()
    root_wsl = windows_path_to_wsl_path(root_windows)

    if simulation_type == "2D":
        runner_file = "openfoam/runner.py"

    elif simulation_type == "3D":
        runner_file = "openfoam/runner_3D.py"

    else:
        raise ValueError(f"Unsupported simulation type: {simulation_type}")

    command = (
        f"cd {shlex.quote(root_wsl)} && "
        f"python3 {runner_file} {shlex.quote(case_name)}"
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