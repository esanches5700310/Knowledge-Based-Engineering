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
# Basic scenario inputs
# ----------------------------------------------------------------------

CASE_NAME = "case_003_slope_jet_bed_slope_2d"
TEMPLATE_NAME = "slope_jet_bed_slope_2d"

# Geometry [m, deg]
WATER_DEPTH = 5.0
FLAT_BED_LENGTH = 5
SLOPE_ANGLE_DEG = 45
SLOPE_TOP_FRACTION = 1.00
DOMAIN_WIDTH = 0.1

# Localized jet settings
JET_CENTER_Z = 1.0
JET_HEIGHT = 0.8 # this indicates the effective diameter of the jet velocity inlet

# Flow settings
JET_VELOCITY = 5.0
KINEMATIC_VISCOSITY = 1.0e-6

# Mesh settings # TODO: create function that makes the mesh settings according to domain size
CELLS_FLAT_X = 100
CELLS_SLOPE_X = 100
CELLS_Z = 500

# Post-processing setting
NEAR_WALL_HEIGHT = 0.10


# ----------------------------------------------------------------------
# Useful paths
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

def jet_z_min():
    """Lower height of the localized jet inlet."""
    return JET_CENTER_Z - 0.5 * JET_HEIGHT


def jet_z_max():
    """Upper height of the localized jet inlet."""
    return JET_CENTER_Z + 0.5 * JET_HEIGHT


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

    if JET_HEIGHT <= 0:
        raise ValueError("JET_HEIGHT must be positive.")

    if jet_z_min() <= 0:
        raise ValueError("The jet is too close to the bed. Increase JET_CENTER_Z or reduce JET_HEIGHT.")

    if jet_z_max() >= WATER_DEPTH:
        raise ValueError("The jet is too close to the water surface. Lower JET_CENTER_Z or reduce JET_HEIGHT.")


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

    Geometry:
    - flat canal bed
    - upward side slope reaching the water surface
    - localized jet patch on the left boundary
    - return/open boundary also on the left boundary
    """

    x0 = 0.0
    x1 = FLAT_BED_LENGTH
    x2 = total_length()

    y0 = 0.0
    y1 = DOMAIN_WIDTH

    z0 = 0.0
    z1 = jet_z_min()
    z2 = jet_z_max()
    z3 = WATER_DEPTH

    # Slope intersections at jet height levels
    xs1 = x_on_slope(z1)
    xs2 = x_on_slope(z2)

    text = f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      blockMeshDict;
}}

convertToMeters 1;

// Generated by case_generator.py
// Corrected CFD setup:
// - localized jet inlet
// - return/open boundary on the left
// - top symmetryPlane
// - upward slope reaches the water surface

vertices
(
    // Flat-bed region, x = 0 to x = flat bed length

    // z = 0
    ({x0:.6g} {y0:.6g} {z0:.6g})     // 0
    ({x1:.6g} {y0:.6g} {z0:.6g})     // 1
    ({x1:.6g} {y1:.6g} {z0:.6g})     // 2
    ({x0:.6g} {y1:.6g} {z0:.6g})     // 3

    // z = jet bottom
    ({x0:.6g} {y0:.6g} {z1:.6g})     // 4
    ({x1:.6g} {y0:.6g} {z1:.6g})     // 5
    ({x1:.6g} {y1:.6g} {z1:.6g})     // 6
    ({x0:.6g} {y1:.6g} {z1:.6g})     // 7

    // z = jet top
    ({x0:.6g} {y0:.6g} {z2:.6g})     // 8
    ({x1:.6g} {y0:.6g} {z2:.6g})     // 9
    ({x1:.6g} {y1:.6g} {z2:.6g})     // 10
    ({x0:.6g} {y1:.6g} {z2:.6g})     // 11

    // z = water surface
    ({x0:.6g} {y0:.6g} {z3:.6g})     // 12
    ({x1:.6g} {y0:.6g} {z3:.6g})     // 13
    ({x1:.6g} {y1:.6g} {z3:.6g})     // 14
    ({x0:.6g} {y1:.6g} {z3:.6g})     // 15


    // Slope region points

    // slope at z = jet bottom
    ({xs1:.6g} {y0:.6g} {z1:.6g})    // 16
    ({xs1:.6g} {y1:.6g} {z1:.6g})    // 17

    // slope at z = jet top
    ({xs2:.6g} {y0:.6g} {z2:.6g})    // 18
    ({xs2:.6g} {y1:.6g} {z2:.6g})    // 19

    // slope at water surface
    ({x2:.6g} {y0:.6g} {z3:.6g})     // 20
    ({x2:.6g} {y1:.6g} {z3:.6g})     // 21
);

blocks
(
    // Flat region split into 3 vertical parts
    hex (0 1 2 3 4 5 6 7)
    ({CELLS_FLAT_X} 1 15)
    simpleGrading (1 1 1)

    hex (4 5 6 7 8 9 10 11)
    ({CELLS_FLAT_X} 1 15)
    simpleGrading (1 1 1)

    hex (8 9 10 11 12 13 14 15)
    ({CELLS_FLAT_X} 1 20)
    simpleGrading (1 1 1)


    // Slope region split into 3 vertical parts

    // Lower triangular part, collapsed at the slope toe
    hex (1 1 2 2 5 16 17 6)
    ({CELLS_SLOPE_X} 1 15)
    simpleGrading (1 1 1)

    // Middle slope part
    hex (5 16 17 6 9 18 19 10)
    ({CELLS_SLOPE_X} 1 15)
    simpleGrading (1 1 1)

    // Upper slope part
    hex (9 18 19 10 13 20 21 14)
    ({CELLS_SLOPE_X} 1 20)
    simpleGrading (1 1 1)
);

edges
(
);

boundary
(
    jetInlet
    {{
        type patch;
        faces
        (
            (4 8 11 7)
        );
    }}

    returnOutlet
    {{
        type patch;
        faces
        (
            (0 4 7 3)
            (8 12 15 11)
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
            (1 16 17 2)
            (16 18 19 17)
            (18 20 21 19)
        );
    }}

    top
    {{
        type symmetryPlane;
        faces
        (
            (12 13 14 15)
            (13 20 21 14)
        );
    }}

    frontAndBack
    {{
        type empty;
        faces
        (
            // Flat region
            (0 1 5 4)
            (3 7 6 2)
            (4 5 9 8)
            (7 11 10 6)
            (8 9 13 12)
            (11 15 14 10)

            // Slope region
            (1 1 16 5)
            (2 6 17 2)
            (5 16 18 9)
            (6 10 19 17)
            (9 18 20 13)
            (10 14 21 19)
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

    text = f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       volVectorField;
    object      U;
}}

dimensions      [0 1 -1 0 0 0 0];

internalField   uniform (0 0 0);

boundaryField
{{
    jetInlet
    {{
        type fixedValue;
        value uniform ({JET_VELOCITY:.6g} 0 0);
    }}

    returnOutlet
    {{
        type inletOutlet;
        inletValue uniform (0 0 0);
        value uniform (0 0 0);
    }}

    flatBed
    {{
        type noSlip;
    }}

    slope
    {{
        type noSlip;
    }}

    top
    {{
        type symmetryPlane;
    }}

    frontAndBack
    {{
        type empty;
    }}
}}
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
    jetInlet
    {
        type zeroGradient;
    }

    returnOutlet
    {
        type fixedValue;
        value uniform 0;
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
    jetInlet
    {
        type fixedValue;
        value uniform 0.006;
    }

    returnOutlet
    {
        type inletOutlet;
        inletValue uniform 0.006;
        value uniform 0.006;
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
    jetInlet
    {
        type fixedValue;
        value uniform 0.001;
    }

    returnOutlet
    {
        type inletOutlet;
        inletValue uniform 0.001;
        value uniform 0.001;
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
    jetInlet
    {
        type calculated;
        value uniform 0;
    }

    returnOutlet
    {
        type calculated;
        value uniform 0;
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
        "jet_center_z": JET_CENTER_Z,
        "jet_height": JET_HEIGHT,
        "jet_z_min": jet_z_min(),
        "jet_z_max": jet_z_max(),
    }

    path = case_dir / "case_metadata.json"
    path.write_text(json.dumps(data, indent=4))


if __name__ == "__main__":
    create_case()