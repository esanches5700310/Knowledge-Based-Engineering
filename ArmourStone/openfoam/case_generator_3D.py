"""
case_generator_3d.py

Creates a simplified 3D OpenFOAM case:
- large closed water domain
- flat canal bed
- upward side slope reaching the water surface
- internal propeller / actuator-disk-like source zone
- no inlet or outlet boundary near the propeller

The aim is to reduce the artificial 2D return-flow problem by allowing the
flow to spread in the y-direction.
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

CASE_NAME = "case_005_slope_jet_bed_slope_large_3d"
TEMPLATE_NAME = "slope_jet_bed_slope_large_3d"

# Geometry [m, deg]
WATER_DEPTH = 5.0
FLAT_BED_LENGTH = 30.0
SLOPE_ANGLE_DEG = 29.36
SLOPE_TOP_FRACTION = 1.0

# 3D width
DOMAIN_WIDTH = 12.0

# Propeller / actuator disk source
PROPELLER_DISTANCE_TO_SLOPE_TOE = 10.0
PROPELLER_CENTER_Y = DOMAIN_WIDTH / 2.0
PROPELLER_CENTER_Z = 1.2
PROPELLER_DIAMETER = 0.8
PROPELLER_ZONE_LENGTH = 0.8
JET_VELOCITY = 3.0

# Fluid settings
KINEMATIC_VISCOSITY = 1.0e-6

# Mesh settings
# Keep this coarse first; 3D grows quickly.
CELLS_FLAT_X = 180
CELLS_SLOPE_X = 60
CELLS_Y = 36
CELLS_Z = 50

# Post-processing
NEAR_WALL_HEIGHT = 0.10


# ----------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------
def armourstone_folder():
    return Path(__file__).resolve().parents[1]


def template_folder():
    return armourstone_folder() / "openfoam" / "templates" / TEMPLATE_NAME


def case_folder():
    return armourstone_folder() / "cases" / CASE_NAME


# ----------------------------------------------------------------------
# Geometry calculations
# ----------------------------------------------------------------------
def slope_top_z():
    return SLOPE_TOP_FRACTION * WATER_DEPTH


def slope_run():
    return slope_top_z() / tan(radians(SLOPE_ANGLE_DEG))


def total_length():
    return FLAT_BED_LENGTH + slope_run()


def propeller_x_center():
    return FLAT_BED_LENGTH - PROPELLER_DISTANCE_TO_SLOPE_TOE


def propeller_x_min():
    return propeller_x_center() - 0.5 * PROPELLER_ZONE_LENGTH


def propeller_x_max():
    return propeller_x_center() + 0.5 * PROPELLER_ZONE_LENGTH


def propeller_y_min():
    return PROPELLER_CENTER_Y - 0.5 * PROPELLER_DIAMETER


def propeller_y_max():
    return PROPELLER_CENTER_Y + 0.5 * PROPELLER_DIAMETER


def propeller_z_min():
    return PROPELLER_CENTER_Z - 0.5 * PROPELLER_DIAMETER


def propeller_z_max():
    return PROPELLER_CENTER_Z + 0.5 * PROPELLER_DIAMETER


def check_inputs():
    if WATER_DEPTH <= 0:
        raise ValueError("WATER_DEPTH must be positive.")

    if FLAT_BED_LENGTH <= 0:
        raise ValueError("FLAT_BED_LENGTH must be positive.")

    if DOMAIN_WIDTH <= 0:
        raise ValueError("DOMAIN_WIDTH must be positive.")

    if not 0.0 < SLOPE_TOP_FRACTION <= 1.0:
        raise ValueError("SLOPE_TOP_FRACTION must be larger than 0 and at most 1.")

    if not 5.0 <= SLOPE_ANGLE_DEG <= 80.0:
        raise ValueError("SLOPE_ANGLE_DEG should be between 5 and 80 degrees.")

    if PROPELLER_DIAMETER <= 0:
        raise ValueError("PROPELLER_DIAMETER must be positive.")

    if PROPELLER_ZONE_LENGTH <= 0:
        raise ValueError("PROPELLER_ZONE_LENGTH must be positive.")

    if JET_VELOCITY <= 0:
        raise ValueError("JET_VELOCITY must be positive.")

    if KINEMATIC_VISCOSITY <= 0:
        raise ValueError("KINEMATIC_VISCOSITY must be positive.")

    if propeller_x_min() <= 0:
        raise ValueError("Propeller source is too close to the far-left boundary.")

    if propeller_x_max() >= FLAT_BED_LENGTH:
        raise ValueError("Propeller source must be upstream of the slope toe.")

    if propeller_y_min() <= 0 or propeller_y_max() >= DOMAIN_WIDTH:
        raise ValueError("Propeller source is too close to the side boundaries.")

    if propeller_z_min() <= 0:
        raise ValueError("Propeller source is too close to the bed.")

    if propeller_z_max() >= WATER_DEPTH:
        raise ValueError("Propeller source is too close to the water surface.")


# ----------------------------------------------------------------------
# Main case generation function
# ----------------------------------------------------------------------
def create_case():
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
    write_turbulence_properties(case_dir)
    write_control_dict(case_dir)
    write_fv_schemes(case_dir)
    write_fv_solution(case_dir)

    write_topo_set_dict(case_dir)
    write_fv_options(case_dir)

    write_metadata(case_dir)

    print("Created 3D OpenFOAM case:")
    print(case_dir)
    print()
    print(f"Water depth:        {WATER_DEPTH:.2f} m")
    print(f"Domain width:       {DOMAIN_WIDTH:.2f} m")
    print(f"Flat bed length:    {FLAT_BED_LENGTH:.2f} m")
    print(f"Slope run:          {slope_run():.2f} m")
    print(f"Total length:       {total_length():.2f} m")
    print(f"Propeller x centre: {propeller_x_center():.2f} m")
    print(f"Propeller y centre: {PROPELLER_CENTER_Y:.2f} m")
    print(f"Propeller z centre: {PROPELLER_CENTER_Z:.2f} m")
    print(f"Approx. cell count: {(CELLS_FLAT_X + CELLS_SLOPE_X) * CELLS_Y * CELLS_Z}")

    return case_dir


# ----------------------------------------------------------------------
# OpenFOAM file writers
# ----------------------------------------------------------------------

def write_block_mesh_dict(case_dir):
    """Write a 3D mesh.

    Coordinate system:
    x = direction from propeller toward slope
    y = channel width
    z = vertical direction
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
    // Rectangular region above flat bed
    hex (0 1 2 3 4 5 6 7)
    ({CELLS_FLAT_X} {CELLS_Y} {CELLS_Z})
    simpleGrading (1 1 1)

    // Collapsed slope region
    hex (1 8 9 2 5 8 9 6)
    ({CELLS_SLOPE_X} {CELLS_Y} {CELLS_Z})
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

    sideLeft
    {{
        type symmetryPlane;
        faces
        (
            (0 1 5 4)
            (1 8 8 5)
        );
    }}

    sideRight
    {{
        type symmetryPlane;
        faces
        (
            (3 7 6 2)
            (2 6 9 9)
        );
    }}
);

mergePatchPairs
(
);
"""

    (case_dir / "system" / "blockMeshDict").write_text(text)


def write_U_file(case_dir):
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

    sideLeft
    {
        type symmetryPlane;
    }

    sideRight
    {
        type symmetryPlane;
    }
}
"""
    (case_dir / "0" / "U").write_text(text)


def write_p_file(case_dir):
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

    sideLeft
    {
        type symmetryPlane;
    }

    sideRight
    {
        type symmetryPlane;
    }
}
"""
    (case_dir / "0" / "p").write_text(text)


def write_k_file(case_dir):
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

    sideLeft
    {
        type symmetryPlane;
    }

    sideRight
    {
        type symmetryPlane;
    }
}
"""
    (case_dir / "0" / "k").write_text(text)


def write_epsilon_file(case_dir):
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

    sideLeft
    {
        type symmetryPlane;
    }

    sideRight
    {
        type symmetryPlane;
    }
}
"""
    (case_dir / "0" / "epsilon").write_text(text)


def write_nut_file(case_dir):
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

    sideLeft
    {
        type symmetryPlane;
    }

    sideRight
    {
        type symmetryPlane;
    }
}
"""
    (case_dir / "0" / "nut").write_text(text)


def write_transport_properties(case_dir):
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
    (case_dir / "constant" / "transportProperties").write_text(text)


def write_turbulence_properties(case_dir):
    text = """FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      turbulenceProperties;
}

simulationType RAS;

RAS
{
    RASModel        kEpsilon;
    turbulence      on;
    printCoeffs     on;
}
"""
    (case_dir / "constant" / "turbulenceProperties").write_text(text)


def write_control_dict(case_dir):
    text = """FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      controlDict;
}

application     simpleFoam;

startFrom       startTime;
startTime       0;

stopAt          endTime;
endTime         2500;

deltaT          1;

writeControl    timeStep;
writeInterval   200;

purgeWrite      0;

writeFormat     ascii;
writePrecision  6;
writeCompression off;

timeFormat      general;
timePrecision   6;

runTimeModifiable true;
"""
    (case_dir / "system" / "controlDict").write_text(text)


def write_fv_schemes(case_dir):
    text = """FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      fvSchemes;
}

ddtSchemes
{
    default         steadyState;
}

gradSchemes
{
    default         Gauss linear;
}

divSchemes
{
    div(phi,U)        bounded Gauss upwind;
    div(phi,k)        bounded Gauss upwind;
    div(phi,epsilon)  bounded Gauss upwind;
    div(phi,R)        bounded Gauss upwind;
    div(R)            Gauss linear;
    div(phi,nuTilda)  bounded Gauss upwind;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}

laplacianSchemes
{
    default         Gauss linear corrected;
}

interpolationSchemes
{
    default         linear;
}

snGradSchemes
{
    default         corrected;
}

wallDist
{
    method meshWave;
}
"""
    (case_dir / "system" / "fvSchemes").write_text(text)


def write_fv_solution(case_dir):
    text = """FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      fvSolution;
}

solvers
{
    p
    {
        solver          GAMG;
        tolerance       1e-06;
        relTol          0.1;
        smoother        GaussSeidel;
    }

    U
    {
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       1e-05;
        relTol          0.1;
    }

    k
    {
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       1e-05;
        relTol          0.1;
    }

    epsilon
    {
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       1e-05;
        relTol          0.1;
    }
}

SIMPLE
{
    nNonOrthogonalCorrectors 0;

    pRefCell        0;
    pRefValue       0;

    residualControl
    {
        p               1e-4;
        U               1e-4;
        k               1e-4;
        epsilon         1e-4;
    }
}

relaxationFactors
{
    fields
    {
        p               0.3;
    }

    equations
    {
        U               0.5;
        k               0.5;
        epsilon         0.5;
    }
}
"""
    (case_dir / "system" / "fvSolution").write_text(text)


def write_topo_set_dict(case_dir):
    """Create a box cellZone for the internal propeller source.

    This is a simple rectangular source region. It is not a true circular disk yet,
    but in 3D it is already much closer than the old 2D slot jet.
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
        box     ({propeller_x_min():.6g} {propeller_y_min():.6g} {propeller_z_min():.6g})
                ({propeller_x_max():.6g} {propeller_y_max():.6g} {propeller_z_max():.6g});
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
    (case_dir / "system" / "topoSetDict").write_text(text)


def write_fv_options(case_dir):
    """Apply a simplified internal propeller forcing."""

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
    (case_dir / "constant" / "fvOptions").write_text(text)


def write_metadata(case_dir):
    data = {
        "case_name": CASE_NAME,
        "dimension": "3D",
        "water_depth": WATER_DEPTH,
        "flat_bed_length": FLAT_BED_LENGTH,
        "slope_angle_deg": SLOPE_ANGLE_DEG,
        "slope_top_fraction": SLOPE_TOP_FRACTION,
        "slope_top_z": slope_top_z(),
        "slope_run": slope_run(),
        "total_length": total_length(),
        "domain_width": DOMAIN_WIDTH,
        "kinematic_viscosity": KINEMATIC_VISCOSITY,
        "near_wall_height": NEAR_WALL_HEIGHT,
        "jet_velocity": JET_VELOCITY,
        "propeller_distance_to_slope_toe": PROPELLER_DISTANCE_TO_SLOPE_TOE,
        "propeller_center_x": propeller_x_center(),
        "propeller_x_min": propeller_x_min(),
        "propeller_x_max": propeller_x_max(),
        "propeller_center_y": PROPELLER_CENTER_Y,
        "propeller_y_min": propeller_y_min(),
        "propeller_y_max": propeller_y_max(),
        "propeller_center_z": PROPELLER_CENTER_Z,
        "propeller_z_min": propeller_z_min(),
        "propeller_z_max": propeller_z_max(),
        "propeller_diameter": PROPELLER_DIAMETER,
        "propeller_zone_length": PROPELLER_ZONE_LENGTH,
        "cells_flat_x": CELLS_FLAT_X,
        "cells_slope_x": CELLS_SLOPE_X,
        "cells_y": CELLS_Y,
        "cells_z": CELLS_Z,
    }

    (case_dir / "case_metadata.json").write_text(json.dumps(data, indent=4))


if __name__ == "__main__":
    create_case()