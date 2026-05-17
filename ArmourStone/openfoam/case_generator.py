"""
case_generator.py

Creates an OpenFOAM case for the simplified canal geometry:
- flat horizontal bottom
- upward canal side slope reaching the water surface
- no berm

The case is copied from the template folder and then some OpenFOAM
dictionary files are overwritten using the scenario inputs.
"""

import json
import shutil
from math import tan, radians
from pathlib import Path


# ----------------------------------------------------------------------
# Case Settings

# Default values used only when this file is run directly.
# When the KBE app is used, these values are overwritten by cfd_interface.py.
# ----------------------------------------------------------------------

CASE_NAME = "case_004_slope_jet_bed_slope_large_2d"
TEMPLATE_NAME = "slope_jet_bed_slope_large_2d"

# Geometry [m, deg]
WATER_DEPTH = 5.0
FLAT_BED_LENGTH = 30.0
SLOPE_ANGLE_DEG = 29.36
SLOPE_TOP_FRACTION = 1.00
DOMAIN_WIDTH = 0.1

# Internal propeller / actuator-disk source
PROPELLER_DISTANCE_TO_SLOPE_TOE = 10.0
PROPELLER_CENTER_Z = 1.2
PROPELLER_DIAMETER = 0.8
PROPELLER_ZONE_LENGTH = 0.8
JET_VELOCITY = 3.0

# Fluid settings
KINEMATIC_VISCOSITY = 1.0e-6

# Mesh settings # TODO: create function that makes the mesh settings according to domain size
CELLS_FLAT_X = 240
CELLS_SLOPE_X = 80
CELLS_Z = 80

# Post-processing setting
NEAR_WALL_HEIGHT = 0.10

# ----------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------

def armourstone_folder():
    """Return the ArmourStone folder."""
    return Path(__file__).resolve().parents[1]


def template_folder():
    """Return the OpenFOAM template folder."""
    return armourstone_folder() / "openfoam" / "templates" / TEMPLATE_NAME


def case_folder():
    """Return the case folder."""
    return armourstone_folder() / "cases" / CASE_NAME


# ----------------------------------------------------------------------
# Geometry calculations
# ----------------------------------------------------------------------

def slope_top_z():
    """Height reached by the side slope."""
    return SLOPE_TOP_FRACTION * WATER_DEPTH


def slope_run():
    """Horizontal distance of the upward slope."""
    return slope_top_z() / tan(radians(SLOPE_ANGLE_DEG))


def total_length():
    """Total length of the CFD domain."""
    return FLAT_BED_LENGTH + slope_run()

def propeller_x_center():
    """x-location of the propeller centre."""
    return FLAT_BED_LENGTH - PROPELLER_DISTANCE_TO_SLOPE_TOE


def propeller_x_min():
    """Start of the propeller source zone."""
    return propeller_x_center() - 0.5 * PROPELLER_ZONE_LENGTH


def propeller_x_max():
    """End of the propeller source zone."""
    return propeller_x_center() + 0.5 * PROPELLER_ZONE_LENGTH


def propeller_z_min():
    """Bottom of the propeller source zone."""
    return PROPELLER_CENTER_Z - 0.5 * PROPELLER_DIAMETER


def propeller_z_max():
    """Top of the propeller source zone."""
    return PROPELLER_CENTER_Z + 0.5 * PROPELLER_DIAMETER


def x_on_slope(z):
    """Return x-coordinate where a horizontal z-level meets the slope."""
    return FLAT_BED_LENGTH + z / WATER_DEPTH * slope_run()

def check_inputs():
    """Basic safety checks before generating the case."""
    if WATER_DEPTH <= 0:
        raise ValueError("WATER_DEPTH must be positive.")

    if FLAT_BED_LENGTH <= 0:
        raise ValueError("FLAT_BED_LENGTH must be positive.")

    if not 0.0 < SLOPE_TOP_FRACTION <= 1.0:
        raise ValueError("SLOPE_TOP_FRACTION must be larger than 0 and at most 1.")

    if not 5.0 <= SLOPE_ANGLE_DEG <= 80.0:
        raise ValueError("SLOPE_ANGLE_DEG should be between 5 and 60 degrees.")

    if DOMAIN_WIDTH <= 0:
        raise ValueError("DOMAIN_WIDTH must be positive.")

    if JET_VELOCITY <= 0:
        raise ValueError("JET_VELOCITY must be positive.")

    if KINEMATIC_VISCOSITY <= 0:
        raise ValueError("KINEMATIC_VISCOSITY must be positive.")


    if PROPELLER_DIAMETER <= 0:
        raise ValueError("PROPELLER_DIAMETER must be positive.")

    if PROPELLER_ZONE_LENGTH <= 0:
        raise ValueError("PROPELLER_ZONE_LENGTH must be positive.")

    if propeller_x_min() <= 0:
        raise ValueError("Propeller zone is too close to the far-left boundary.")

    if propeller_x_max() >= FLAT_BED_LENGTH:
        raise ValueError("Propeller zone must be upstream of the slope toe.")

    if propeller_z_min() <= 0:
        raise ValueError("Propeller is too close to the bed.")

    if propeller_z_max() >= WATER_DEPTH:
        raise ValueError("Propeller is too close to the water surface.")

# ----------------------------------------------------------------------
# Main case generation function
# ----------------------------------------------------------------------

def create_case():
    """Create the OpenFOAM case from the template."""
    check_inputs()

    template_dir = template_folder()
    case_dir = case_folder()

    if not template_dir.exists():
        raise FileNotFoundError(f"Template folder not found: {template_dir}")

    if case_dir.exists():
        shutil.rmtree(case_dir)

    shutil.copytree(template_dir, case_dir)

    write_block_mesh_dict(case_dir)

    write_U_file(case_dir)
    write_p_file(case_dir)
    write_k_file(case_dir)
    write_epsilon_file(case_dir)
    write_nut_file(case_dir)

    write_transport_properties(case_dir)
    write_topo_set_dict(case_dir)
    write_fv_options(case_dir)
    write_sample_dict(case_dir)
    write_metadata(case_dir)

    print("Created OpenFOAM case:")
    print(case_dir)
    print()
    print(f"Water depth:       {WATER_DEPTH:.2f} m")
    print(f"Flat bed length:   {FLAT_BED_LENGTH:.2f} m")
    print(f"Slope top height:  {slope_top_z():.2f} m")
    print(f"Slope run:         {slope_run():.2f} m")
    print(f"Total length:      {total_length():.2f} m")

    return case_dir


# ----------------------------------------------------------------------
# OpenFOAM file writers
# ----------------------------------------------------------------------

def write_block_mesh_dict(case_dir):
    """Write system/blockMeshDict.

    Closed 2D tank model:
    - far-left slip wall
    - flat canal bed
    - upward side slope reaching the water surface
    - propeller source is created internally using topoSet + fvOptions
    """

    x0 = 0.0
    x1 = FLAT_BED_LENGTH
    x2 = total_length()

    y0 = 0.0
    y1 = DOMAIN_WIDTH

    z0 = 0.0
    zh = WATER_DEPTH

    text = f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      blockMeshDict;
}}

convertToMeters 1;

// Generated by case_generator.py
// Closed 2D tank with internal propeller source.
// The side slope reaches the still water line.

vertices
(
    ({x0:.6g} {y0:.6g} {z0:.6g})     // 0
    ({x1:.6g} {y0:.6g} {z0:.6g})     // 1
    ({x1:.6g} {y1:.6g} {z0:.6g})     // 2
    ({x0:.6g} {y1:.6g} {z0:.6g})     // 3

    ({x0:.6g} {y0:.6g} {zh:.6g})     // 4
    ({x1:.6g} {y0:.6g} {zh:.6g})     // 5
    ({x1:.6g} {y1:.6g} {zh:.6g})     // 6
    ({x0:.6g} {y1:.6g} {zh:.6g})     // 7

    ({x2:.6g} {y0:.6g} {zh:.6g})     // 8
    ({x2:.6g} {y1:.6g} {zh:.6g})     // 9
);

blocks
(
    hex (0 1 2 3 4 5 6 7)
    ({CELLS_FLAT_X} 1 {CELLS_Z})
    simpleGrading (1 1 1)

    // Collapsed block for triangular water region above the slope
    hex (1 8 9 2 5 8 9 6)
    ({CELLS_SLOPE_X} 1 {CELLS_Z})
    simpleGrading (1 1 1)
);

edges
(
);

boundary
(
    farLeft
    {{
        type symmetryPlane;
        faces
        (
            (0 4 7 3)
        );
    }}

    flatBed
    {{
        type wall;
        faces
        (
            (0 3 2 1)
        );
    }}

    slope
    {{
        type wall;
        faces
        (
            (1 8 9 2)
        );
    }}

    top
    {{
        type symmetryPlane;
        faces
        (
            (4 5 6 7)
            (5 8 9 6)
        );
    }}

    frontAndBack
    {{
        type empty;
        faces
        (
            (0 1 5 4)
            (3 7 6 2)
            (1 8 8 5)
            (2 6 9 9)
        );
    }}
);

mergePatchPairs
(
);
"""

    path = case_dir / "system" / "blockMeshDict"
    path.write_text(text)


def write_U_file(case_dir):
    """Write 0/U."""

    text = """FoamFile
{
    version     2.0;
    format      ascii;
    class       volVectorField;
    object      U;
}

dimensions      [0 1 -1 0 0 0 0];

internalField   uniform (0 0 0);

boundaryField
{
    farLeft
    {
        type symmetryPlane;
    }

    flatBed
    {
        type noSlip;
    }

    slope
    {
        type noSlip;
    }

    top
    {
        type symmetryPlane;
    }

    frontAndBack
    {
        type empty;
    }
}
"""

    path = case_dir / "0" / "U"
    path.write_text(text)


def write_p_file(case_dir):
    """Write 0/p."""

    text = """FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    object      p;
}

dimensions      [0 2 -2 0 0 0 0];

internalField   uniform 0;

boundaryField
{
    farLeft
    {
        type symmetryPlane;
    }

    flatBed
    {
        type zeroGradient;
    }

    slope
    {
        type zeroGradient;
    }

    top
    {
        type symmetryPlane;
    }

    frontAndBack
    {
        type empty;
    }
}
"""

    path = case_dir / "0" / "p"
    path.write_text(text)

def write_k_file(case_dir):
    """Write 0/k."""

    text = """FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    object      k;
}

dimensions      [0 2 -2 0 0 0 0];

internalField   uniform 0.006;

boundaryField
{
    farLeft
    {
        type symmetryPlane;
    }

    flatBed
    {
        type kqRWallFunction;
        value uniform 0.006;
    }

    slope
    {
        type kqRWallFunction;
        value uniform 0.006;
    }

    top
    {
        type symmetryPlane;
    }

    frontAndBack
    {
        type empty;
    }
}
"""

    path = case_dir / "0" / "k"
    path.write_text(text)


def write_epsilon_file(case_dir):
    """Write 0/epsilon."""

    text = """FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    object      epsilon;
}

dimensions      [0 2 -3 0 0 0 0];

internalField   uniform 0.001;

boundaryField
{
    farLeft
    {
        type symmetryPlane;
    }

    flatBed
    {
        type epsilonWallFunction;
        value uniform 0.001;
    }

    slope
    {
        type epsilonWallFunction;
        value uniform 0.001;
    }

    top
    {
        type symmetryPlane;
    }

    frontAndBack
    {
        type empty;
    }
}
"""

    path = case_dir / "0" / "epsilon"
    path.write_text(text)

def write_nut_file(case_dir):
    """Write 0/nut."""

    text = """FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    object      nut;
}

dimensions      [0 2 -1 0 0 0 0];

internalField   uniform 0;

boundaryField
{
    farLeft
    {
        type symmetryPlane;
    }

    flatBed
    {
        type nutkWallFunction;
        value uniform 0;
    }

    slope
    {
        type nutkWallFunction;
        value uniform 0;
    }

    top
    {
        type symmetryPlane;
    }

    frontAndBack
    {
        type empty;
    }
}
"""

    path = case_dir / "0" / "nut"
    path.write_text(text)


def write_transport_properties(case_dir):
    """Write constant/transportProperties."""

    text = f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      transportProperties;
}}

transportModel  Newtonian;

nu              [0 2 -1 0 0 0 0] {KINEMATIC_VISCOSITY:.6g};
"""

    path = case_dir / "constant" / "transportProperties"
    path.write_text(text)


def write_sample_dict(case_dir):
    """Write system/sampleDict.

    This is useful later if OpenFOAM sampling is working.
    The Python postprocessor does not depend on this file.
    """

    y_mid = DOMAIN_WIDTH / 2.0

    text = f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      sampleDict;
}}

type sets;

libs ("libsampling.so");

interpolationScheme cellPoint;

setFormat raw;

sets
(
    flatBedLine
    {{
        type uniform;
        axis distance;
        start (0.2 {y_mid:.6g} {NEAR_WALL_HEIGHT:.6g});
        end   ({FLAT_BED_LENGTH - 0.2:.6g} {y_mid:.6g} {NEAR_WALL_HEIGHT:.6g});
        nPoints 100;
    }}

    slopeLine
    {{
        type uniform;
        axis distance;
        start ({FLAT_BED_LENGTH + 0.1:.6g} {y_mid:.6g} {NEAR_WALL_HEIGHT:.6g});
        end   ({total_length() - 0.2:.6g} {y_mid:.6g} {slope_top_z() - NEAR_WALL_HEIGHT:.6g});
        nPoints 100;
    }}
);

fields
(
    U
    p
);
"""

    path = case_dir / "system" / "sampleDict"
    path.write_text(text)


def write_metadata(case_dir):
    """Write a small JSON file with the scenario settings.

    This makes post-processing easier because it knows where the flat bed
    and slope are located.
    """

    data = {
        "case_name": CASE_NAME,
        "water_depth": WATER_DEPTH,
        "flat_bed_length": FLAT_BED_LENGTH,
        "slope_angle_deg": SLOPE_ANGLE_DEG,
        "slope_top_fraction": SLOPE_TOP_FRACTION,
        "slope_top_z": slope_top_z(),
        "slope_run": slope_run(),
        "total_length": total_length(),
        "domain_width": DOMAIN_WIDTH,
        "jet_velocity": JET_VELOCITY,
        "kinematic_viscosity": KINEMATIC_VISCOSITY,
        "near_wall_height": NEAR_WALL_HEIGHT,

        "propeller_distance_to_slope_toe": PROPELLER_DISTANCE_TO_SLOPE_TOE,
        "propeller_center_x": propeller_x_center(),
        "propeller_x_min": propeller_x_min(),
        "propeller_x_max": propeller_x_max(),
        "propeller_center_z": PROPELLER_CENTER_Z,
        "propeller_z_min": propeller_z_min(),
        "propeller_z_max": propeller_z_max(),
        "propeller_diameter": PROPELLER_DIAMETER,
        "propeller_zone_length": PROPELLER_ZONE_LENGTH,
    }

    path = case_dir / "case_metadata.json"
    path.write_text(json.dumps(data, indent=4))

def write_topo_set_dict(case_dir):
    """Write system/topoSetDict.

    This selects the internal propeller source region.
    """

    text = f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      topoSetDict;
}}

actions
(
    {{
        name    propellerSet;
        type    cellSet;
        action  new;
        source  boxToCell;
        box     ({propeller_x_min():.6g} 0 {propeller_z_min():.6g})
                ({propeller_x_max():.6g} {DOMAIN_WIDTH:.6g} {propeller_z_max():.6g});
    }}

    {{
        name    propellerZone;
        type    cellZoneSet;
        action  new;
        source  setToCellZone;
        set     propellerSet;
    }}
);
"""

    path = case_dir / "system" / "topoSetDict"
    path.write_text(text)

def write_fv_options(case_dir):
    """Write constant/fvOptions.

    The propeller is represented as a simplified internal momentum source.
    """

    text = f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      fvOptions;
}}

propellerJet
{{
    type            meanVelocityForce;
    active          yes;

    selectionMode   cellZone;
    cellZone        propellerZone;

    fields          (U);
    Ubar            ({JET_VELOCITY:.6g} 0 0);
    relaxation      0.2;
}}
"""

    path = case_dir / "constant" / "fvOptions"
    path.write_text(text)

if __name__ == "__main__":
    create_case()