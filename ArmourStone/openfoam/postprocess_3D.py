"""
postprocess_3D.py

Reads the 3D OpenFOAM results and extracts:
- maximum velocity near the flat bed
- maximum velocity near the upward side slope
- governing velocity for the armour-stone calculation

This script uses the latest OpenFOAM time folder.

Compared to the 2D postprocess file, this version:
- uses the 3D case name
- keeps the y-coordinate as a real channel-width coordinate
- reports the location of the maximum velocity
- writes separate 3D output files
"""

import csv
import json
import math
import re
from pathlib import Path

# -----------------------------------------------------------------------------
# Case configuration and parsing settings
# -----------------------------------------------------------------------------
CASE_NAME = "case_005_slope_jet_bed_slope_large_3d"
# CASE_NAME is later changed according to input project name

VECTOR_PATTERN = re.compile(
    r"\(\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*\)"
)

# -----------------------------------------------------------------------------
# Functions used to define project, case and output paths
# -----------------------------------------------------------------------------
def armourstone_folder():
    """Return the ArmourStone folder."""
    return Path(__file__).resolve().parents[1]


def case_folder():
    """Return the OpenFOAM case folder."""
    return armourstone_folder() / "cases" / CASE_NAME


def output_folder():
    """Return the folder where CFD results will be written."""
    folder = armourstone_folder() / "output" / "cfd_results" / CASE_NAME
    folder.mkdir(parents=True, exist_ok=True)
    return folder

# -----------------------------------------------------------------------------
# Functions used to read OpenFOAM result files
# -----------------------------------------------------------------------------
def get_latest_time_folder(case_dir):
    """Find the latest numeric OpenFOAM result folder."""
    time_folders = []

    for item in case_dir.iterdir():
        if item.is_dir():
            try:
                time_value = float(item.name)
                time_folders.append((time_value, item))
            except ValueError:
                pass

    if not time_folders:
        raise FileNotFoundError("No OpenFOAM time folders found.")

    return max(time_folders, key=lambda pair: pair[0])[1]


def read_metadata(case_dir):
    """Read the case metadata written by case_generator_3D.py."""
    path = case_dir / "case_metadata.json"

    if not path.exists():
        raise FileNotFoundError(
            "case_metadata.json was not found. "
            "Run case_generator_3D.py before post-processing."
        )

    return json.loads(path.read_text())


def read_vector_file(path):
    """Read only the internalField vectors from an OpenFOAM vector field file.

    This is used for:
    - U: velocity vectors
    - C: cell centre coordinates

    It ignores boundaryField vectors, because those are not cell values.
    """

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    text = path.read_text(errors="ignore")

    number_match = re.search(
        r"internalField\s+nonuniform\s+List<vector>\s+(\d+)",
        text
    )

    if number_match is None:
        raise ValueError(f"Could not find internalField List<vector> in {path}")

    number_of_vectors = int(number_match.group(1))
    start_index = number_match.end()
    remaining_text = text[start_index:]

    all_vectors = []

    for match in VECTOR_PATTERN.finditer(remaining_text):
        x = float(match.group(1))
        y = float(match.group(2))
        z = float(match.group(3))
        all_vectors.append((x, y, z))

    if len(all_vectors) < number_of_vectors:
        raise ValueError(
            f"Expected {number_of_vectors} vectors in {path}, "
            f"but only found {len(all_vectors)}."
        )

    return all_vectors[:number_of_vectors]

# -----------------------------------------------------------------------------
# Functions used for geometric and velocity calculations
# -----------------------------------------------------------------------------
def vector_magnitude(vector):
    """Return magnitude of a 3D vector."""
    x, y, z = vector
    return math.sqrt(x * x + y * y + z * z)


def bed_height_at_x(x, metadata):
    """Return the bed/slope height for a given x-position."""
    flat_length = metadata["flat_bed_length"]
    total_length = metadata["total_length"]
    slope_top_z = metadata["slope_top_z"]

    if x <= flat_length:
        return 0.0

    slope_run = total_length - flat_length
    distance_along_slope = x - flat_length

    return distance_along_slope / slope_run * slope_top_z


def distance_to_slope(x, z, metadata):
    """Calculate distance from point (x, z) to the slope line.

    The slope is treated as a line in the x-z plane and extended across
    the full y-width of the 3D domain.
    """

    x1 = metadata["flat_bed_length"]
    z1 = 0.0

    x2 = metadata["total_length"]
    z2 = metadata["slope_top_z"]

    numerator = abs((z2 - z1) * x - (x2 - x1) * z + x2 * z1 - z2 * x1)
    denominator = math.sqrt((z2 - z1) ** 2 + (x2 - x1) ** 2)

    return numerator / denominator


def row_from_sample(centre, velocity):
    """Create one CSV row from a cell centre and velocity vector."""
    x, y, z = centre
    ux, uy, uz = velocity
    u_mag = vector_magnitude(velocity)

    return [x, y, z, ux, uy, uz, u_mag]


def max_row(rows):
    """Return the row with the maximum velocity magnitude."""
    if not rows:
        return None

    return max(rows, key=lambda row: row[-1])


def sample_location_from_row(row):
    """Return a readable location dictionary from a sample row."""
    if row is None:
        return None

    return {
        "x": row[0],
        "y": row[1],
        "z": row[2],
        "Ux": row[3],
        "Uy": row[4],
        "Uz": row[5],
        "U_magnitude": row[6],
    }

# -----------------------------------------------------------------------------
# Main post-processing workflow
# -----------------------------------------------------------------------------
def extract_results():
    """Extract near-bed and near-slope velocity results."""
    case_dir = case_folder()
    metadata = read_metadata(case_dir)

    latest_dir = get_latest_time_folder(case_dir)

    velocity_file = latest_dir / "U"
    cell_centre_file = latest_dir / "C"

    if not cell_centre_file.exists():
        raise FileNotFoundError(
            f"Cell centre file not found:\n{cell_centre_file}\n\n"
            "This file is created with:\n"
            "postProcess -func writeCellCentres -latestTime"
        )

    velocities = read_vector_file(velocity_file)
    cell_centres = read_vector_file(cell_centre_file)

    if len(velocities) != len(cell_centres):
        raise ValueError("U and C files do not contain the same number of vectors.")

    flat_bed_rows = []
    slope_rows = []

    flat_length = metadata["flat_bed_length"]
    total_length = metadata["total_length"]
    near_wall_height = metadata["near_wall_height"]

    for centre, velocity in zip(cell_centres, velocities):
        x, y, z = centre

        # Check cells close to the flat bed.
        if 0.0 <= x <= flat_length:
            if 0.0 <= z <= near_wall_height:
                flat_bed_rows.append(row_from_sample(centre, velocity))

        # Check cells close to the upward slope.
        if flat_length <= x <= total_length:
            local_bed_z = bed_height_at_x(x, metadata)
            distance = distance_to_slope(x, z, metadata)

            if z >= local_bed_z and distance <= near_wall_height:
                slope_rows.append(row_from_sample(centre, velocity))

    max_flat_row = max_row(flat_bed_rows)
    max_slope_row = max_row(slope_rows)

    max_flat_velocity = max_flat_row[-1] if max_flat_row is not None else 0.0
    max_slope_velocity = max_slope_row[-1] if max_slope_row is not None else 0.0
    governing_velocity = max(max_flat_velocity, max_slope_velocity)

    if max_flat_velocity >= max_slope_velocity:
        governing_region = "flat_bed"
        governing_row = max_flat_row
    else:
        governing_region = "slope"
        governing_row = max_slope_row

    summary = {
        "case_name": CASE_NAME,
        "dimension": "3D",
        "latest_time": latest_dir.name,
        "number_of_flat_bed_samples": len(flat_bed_rows),
        "number_of_slope_samples": len(slope_rows),
        "max_flat_bed_velocity": max_flat_velocity,
        "max_slope_velocity": max_slope_velocity,
        "governing_velocity": governing_velocity,
        "governing_region": governing_region,
        "max_flat_bed_location": sample_location_from_row(max_flat_row),
        "max_slope_location": sample_location_from_row(max_slope_row),
        "governing_location": sample_location_from_row(governing_row),
    }

    write_csv("flat_bed_velocity_samples_3D.csv", flat_bed_rows)
    write_csv("slope_velocity_samples.csv", slope_rows)
    write_summary(summary)

    print_summary(summary)

    return summary

# -----------------------------------------------------------------------------
# Functions used to write output files and print results
# -----------------------------------------------------------------------------
def write_csv(filename, rows):
    """Write velocity samples to CSV."""
    path = output_folder() / filename

    header = ["x", "y", "z", "Ux", "Uy", "Uz", "U_magnitude"]

    with path.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)


def write_summary(summary):
    """Write summary results to JSON."""
    path = output_folder() / "hydraulic_loading_summary.json"
    path.write_text(json.dumps(summary, indent=4))


def print_location(label, location):
    """Print a maximum-velocity location."""
    if location is None:
        print(f"{label}: not found")
        return

    print(
        f"{label}: "
        f"x = {location['x']:.3f} m, "
        f"y = {location['y']:.3f} m, "
        f"z = {location['z']:.3f} m"
    )


def print_summary(summary):
    """Print the main 3D CFD results."""
    print("\n3D CFD hydraulic loading summary")
    print("--------------------------------")
    print(f"Latest time:             {summary['latest_time']}")
    print(f"Flat bed samples:        {summary['number_of_flat_bed_samples']}")
    print(f"Slope samples:           {summary['number_of_slope_samples']}")
    print(f"Max flat bed velocity:   {summary['max_flat_bed_velocity']:.4f} m/s")
    print(f"Max slope velocity:      {summary['max_slope_velocity']:.4f} m/s")
    print(f"Governing velocity:      {summary['governing_velocity']:.4f} m/s")
    print(f"Governing region:        {summary['governing_region']}")

    print_location("Max flat bed location", summary["max_flat_bed_location"])
    print_location("Max slope location", summary["max_slope_location"])
    print_location("Governing location", summary["governing_location"])


if __name__ == "__main__":
    extract_results()
