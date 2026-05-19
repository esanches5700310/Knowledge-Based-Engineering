"""
cfd_interface.py

Interface between the ParaPy/KBE application and the OpenFOAM workflow.

This module translates the high-level KBE model inputs into OpenFOAM case
settings, creates the corresponding CFD case, runs the correct 2D or 3D
OpenFOAM workflow, post-processes the hydraulic loading results, and returns
the governing velocity to the armour stone assessment.

The module is intentionally organized as an interface layer. It does not define
the OpenFOAM mesh dictionaries directly; instead, it passes the selected inputs
to the 2D or 3D case generator modules and then calls the corresponding runner
and postprocessor.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import platform
import subprocess
import shlex


# -----------------------------------------------------------------------------
# Data container used to pass CFD settings through the workflow
# -----------------------------------------------------------------------------

@dataclass
class CFDSettings:
    """Container for all inputs needed to define and run an OpenFOAM case.

    The default values are fallback values. During the normal KBE workflow they
    are overwritten using inputs from the ParaPy model and input.py.
    """

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


# -----------------------------------------------------------------------------
# Path and settings file utilities
# -----------------------------------------------------------------------------

def armourstone_folder():
    """Return the root folder of the ArmourStone application.
    """
    return Path(__file__).resolve().parents[1]

def save_cfd_settings(settings):
    """Save the CFD settings used for a run as a JSON file.

    Parameters
    ----------
    settings : CFDSettings
        The full set of CFD settings used to create, run, and postprocess the
        OpenFOAM case.

    Returns
    -------
    pathlib.Path
        Path to the JSON file containing the stored CFD settings.
    """
    output_dir = armourstone_folder() / "output" / "cfd_settings"
    output_dir.mkdir(parents=True, exist_ok=True)

    path = output_dir / f"{settings.case_name}_settings.json"
    path.write_text(json.dumps(asdict(settings), indent=4))

    return path


def check_simulation_type(simulation_type):
    """Check whether the selected OpenFOAM simulation type is valid.

    The workflow only supports the two case-generator branches currently
    implemented in the app: "2D" and "3D".
    """
    simulation_type = simulation_type.upper()

    if simulation_type not in ["2D", "3D"]:
        raise ValueError(
            "openfoam_simulation_type must be either '2D' or '3D'. "
            f"Received: {simulation_type}"
        )

    return simulation_type


# -----------------------------------------------------------------------------
# Functions used to create CFD settings from the KBE / ParaPy model
# -----------------------------------------------------------------------------

def make_cfd_settings_from_kbe(
            ship,
            waterway,
            jet_velocity,
            simulation_type="2D",
            case_name = None,
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
    """Create a CFDSettings object from the ParaPy/KBE input objects.

    This function is the main translation step between the KBE model and the
    OpenFOAM workflow. It receives the ship and waterway objects from ParaPy,
    combines them with the selected CFD inputs, and produces a single
    ``CFDSettings`` object.

    For both 2D and 3D:
    flat_bed_length = upstream_length + propeller-to-slope distance
    """

    simulation_type = check_simulation_type(simulation_type)

    if case_name is None or str(case_name).strip() == "":
        if simulation_type == "2D":
            case_name = "case_kbe_2d"
        else:
            case_name = "case_kbe_3d"

    case_name = str(case_name).strip()

    if simulation_type == "2D":
        left_boundary_to_propeller = left_boundary_to_propeller_2d
        domain_width = 0.1

        cells_flat_x = cells_flat_x_2d
        cells_slope_x = cells_slope_x_2d
        cells_y = 1
        cells_z = cells_z_2d

    elif simulation_type == "3D":
        left_boundary_to_propeller = left_boundary_to_propeller_3d
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


# -----------------------------------------------------------------------------
# Functions used to apply CFD settings to the OpenFOAM case generators
# -----------------------------------------------------------------------------

def apply_settings_to_2d_case_generator(settings):
    """Apply CFDSettings to the 2D case generator module.

    The 2D case generator uses module-level variables to write the OpenFOAM
    dictionaries. This function overwrites those variables with values from the
    current KBE run before the case is created.
    """

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
    """Apply CFDSettings to the 3D case generator module.

    The 3D case generator follows the same structure as the 2D generator, but
    also receives the domain width, centreline propeller y-position, and y-cell
    count required for the 3D OpenFOAM case.
    """

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


# -----------------------------------------------------------------------------
# Function used to create the OpenFOAM case folder
# -----------------------------------------------------------------------------

def create_openfoam_case(settings):
    """Create the OpenFOAM case folder for the selected simulation type.

    Depending on ``settings.simulation_type``, this function selects the 2D or
    3D case generator, applies the current CFD settings to it, and calls the
    generator's ``create_case`` function.
    """

    if settings.simulation_type == "2D":
        case_generator = apply_settings_to_2d_case_generator(settings)

    elif settings.simulation_type == "3D":
        case_generator = apply_settings_to_3d_case_generator(settings)

    else:
        raise ValueError(f"Unsupported simulation type: {settings.simulation_type}")

    return case_generator.create_case()


# -----------------------------------------------------------------------------
# Functions used to run the complete OpenFOAM workflow
# -----------------------------------------------------------------------------

def run_openfoam_workflow(settings):
    """Run the full CFD workflow and return the hydraulic loading summary.

    The workflow consists of four steps:
    1. validate the selected simulation type;
    2. save the CFD settings for traceability;
    3. generate the OpenFOAM case folder;
    4. run OpenFOAM and postprocess the results.

    On Windows, OpenFOAM is launched through WSL. On Linux/WSL, the runner is
    called directly from Python.
    """

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


def get_governing_velocity(settings):
    """Run the complete CFD workflow (function above) and return only the governing velocity.

    This helper is useful when the KBE app only needs the scalar velocity value
    for the armour stone sizing rule, rather than the full postprocessing
    summary dictionary.
    """
    summary = run_openfoam_workflow(settings)
    return summary["governing_velocity"]


# -----------------------------------------------------------------------------
# Functions used to run OpenFOAM locally or through WSL
# -----------------------------------------------------------------------------

def run_openfoam_runner_locally(settings):
    """Run the correct OpenFOAM runner directly from Linux or WSL.
    """

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


def windows_path_to_wsl_path(path):
    """Convert a Windows path to the corresponding WSL path.

    The OpenFOAM runner is executed inside WSL when the ParaPy app is launched
    from Windows. This conversion is required so that the WSL shell can access
    the same ArmourStone project folder.
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


def run_openfoam_runner_in_wsl(case_name, simulation_type):
    """Run the correct OpenFOAM runner inside WSL from Windows Python.

    This function builds the WSL command used by the ParaPy application on
    Windows. It selects the 2D or 3D runner, passes the case name as a command
    line argument, and raises an error if the WSL/OpenFOAM command fails.
    """

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


# -----------------------------------------------------------------------------
# Function used to postprocess OpenFOAM results
# -----------------------------------------------------------------------------

def postprocess_results(settings):
    """Run the correct postprocessor and return the summary dictionary.

    The postprocessor extracts the near-wall velocities from the latest
    OpenFOAM result folder and writes the CSV/JSON files used by the KBE app.
    This function selects the 2D or 3D postprocessor based on the active CFD
    settings.
    """

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
