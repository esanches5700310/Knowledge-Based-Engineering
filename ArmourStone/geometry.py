import os
import pandas as pd

from parapy import core as ppc
from parapy.core import child
from parapy.geom import Polygon, Sphere, Box, Cylinder, translate, rotate, XOY

"""
geometry.py

This module defines the ParaPy geometry used to visualize the armour stone
assessment case. It generates the waterway domain, ship (simple) representation,
propeller geometry and optional CFD velocity-field visualization.

The geometry adapts automatically to the selected OpenFOAM simulation type:
- for a 2D CFD case, the waterway is shown as a cross-sectional polygon;
- for a 3D CFD case, the waterway is shown as a three-dimensional domain
  using the specified CFD domain width.
"""


class Geometry(ppc.Base):
    """ParaPy geometry for the waterway, ship, propeller and CFD velocity field."""

    waterway = ppc.Input()
    ship = ppc.Input()

    cfd_left_boundary_to_propeller_2d = ppc.Input(
        0.0,
        doc="Distance from the left CFD boundary to the propeller for the 2D case."
    )

    openfoam_simulation_type = ppc.Input(
        "2D",
        doc="OpenFOAM simulation type. Choose '2D' or '3D'."
    )

    cfd_left_boundary_to_propeller_3d = ppc.Input(
        1.0,
        doc="Distance from the left CFD boundary to the propeller for the 3D case."
    )

    cfd_domain_width_3d = ppc.Input(
        12.0,
        doc="Width/depth of the 3D CFD domain. [m]"
    )

    cfd_results_dir = ppc.Input(
        None,
        doc="Folder containing the CFD CSV result files."
    )

    show_velocity_field = ppc.Input(
        True,
        doc="Show the imported CFD velocity field as a coloured point cloud."
    )

    velocity_field_max_points = ppc.Input(
        300,
        doc="Maximum number of CFD velocity points shown in the GUI."
    )

    velocity_field_point_radius = ppc.Input(
        0.05,
        doc="Radius of the CFD velocity point-cloud markers."
    )

    # ---------------------
    # WATERWAY GEOMETRY
    #---------------------
    @ppc.Attribute
    def waterway_surface_points(self):
        """Generate either a 2D waterway polygon or a 3D waterway surface set."""

        x0 = -self.cfd_left_boundary_to_propeller
        x1 = self.waterway.d_slope
        x2 = self.waterway.d_slope + self.waterway.waterway_width

        y0 = 0.0
        y1 = self.gui_domain_width

        z0 = -self.waterway.h
        z1 = 0.0

        # 2D case: one cross-section polygon
        if not self.is_3d_geometry:
            return [
                [
                    (x0, y0, z0),
                    (x1, y0, z0),
                    (x2, y0, z1),
                    (x0, y0, z1),
                ]
            ]

        # 3D case: several surface polygons forming the waterway volume
        return [
            # front side, y = 0
            [
                (x0, y0, z0),
                (x1, y0, z0),
                (x2, y0, z1),
                (x0, y0, z1),
            ],

            # back side, y = domain width
            [
                (x0, y1, z0),
                (x0, y1, z1),
                (x2, y1, z1),
                (x1, y1, z0),
            ],

            # flat bed
            [
                (x0, y0, z0),
                (x0, y1, z0),
                (x1, y1, z0),
                (x1, y0, z0),
            ],

            # sloped bed
            [
                (x1, y0, z0),
                (x1, y1, z0),
                (x2, y1, z1),
                (x2, y0, z1),
            ],

            # top / free surface
            [
                (x0, y0, z1),
                (x2, y0, z1),
                (x2, y1, z1),
                (x0, y1, z1),
            ],

            # far-left boundary
            [
                (x0, y0, z0),
                (x0, y0, z1),
                (x0, y1, z1),
                (x0, y1, z0),
            ],
        ]

    @ppc.Part
    def waterway_shape(self):
        return Polygon(
            self.waterway_surface_points[child.index],
            quantify=len(self.waterway_surface_points),
            color="blue"
        )

    # ---------------------
    # Propeller GEOMETRY
    # ---------------------
    @ppc.Part(parse=False)
    def propeller_shape(self):
        """Generate the propeller geometry.

        2D:
            Simple rectangular actuator region.

        3D:
            Circular disk with diameter equal to ship.D_p,
            centred in the CFD domain width.
        """

        if self.is_3d_geometry:
            return Cylinder(
                radius=0.5 * self.ship.D_p,
                height=self.propeller_disk_thickness,
                position=rotate(
                    translate(
                        XOY,
                        "x", -0.5 * self.propeller_disk_thickness,
                        "y", 0.5 * self.cfd_domain_width_3d,
                        "z", -self.waterway.h + self.ship.Z_p
                    ),
                    "y", 90,
                    deg=True
                ),
                color="red"
            )

        return Box(
            width=0.2,
            length=self.propeller_box_y_length,
            height=self.ship.D_p,
            position=translate(
                XOY,
                "x", -0.2,
                "y", self.propeller_y_position,
                "z", -self.waterway.h + self.ship.Z_p - self.ship.D_p / 2
            ),
            color="red"
        )

    # ---------------------
    # Ship GEOMETRY
    # ---------------------
    @ppc.Part
    def ship_shape(self):
        return Box(
            width=1.9,
            length=self.ship_box_y_length,
            height=self.ship.draught,
            position=translate(
                XOY,
                "x", -2.0,
                "y", self.ship_y_position,
                "z", -self.ship.draught
            ),
            color="black"
        )

    # ---------------------
    # Velocity Field GEOMETRY
    # ---------------------
    @ppc.Part
    def velocity_field(self):
        return VelocityFieldVisualization(
            csv_files=self.velocity_csv_files,
            waterway=self.waterway,
            cfd_x_offset=self.cfd_x_offset,
            max_points=self.velocity_field_max_points,
            point_radius=self.velocity_field_point_radius,
            show=self.show_velocity_field
        )

    # ----------------------------------------------------------------------
    # Helper Functions for reading the velocities from CFD csv data
    # ----------------------------------------------------------------------
    @ppc.Attribute
    def flat_bed_velocity_csv(self):
        """Default OpenFOAM post-processing CSV for the flat bed."""
        if self.cfd_results_dir is None:
            return None

        return os.path.join(
            self.cfd_results_dir,
            "flat_bed_velocity_samples.csv"
        )

    @ppc.Attribute
    def slope_velocity_csv(self):
        """Default OpenFOAM post-processing CSV for the slope."""
        if self.cfd_results_dir is None:
            return None

        return os.path.join(
            self.cfd_results_dir,
            "slope_velocity_samples.csv"
        )

    @ppc.Attribute
    def velocity_csv_files(self):
        """CSV files used for the ParaView-like velocity-field visualization."""
        return [
            filename
            for filename in [
                self.flat_bed_velocity_csv,
                self.slope_velocity_csv
            ]
            if filename is not None
        ]

    def _read_velocity_csv(self, filename):
        """Read a velocity CSV file when it exists."""
        if filename is None or not os.path.exists(filename):
            return None

        return pd.read_csv(filename)

    @ppc.Attribute
    def cfd_x_offset(self):
        """
        Offset between CFD x-coordinate and GUI x-coordinate.

        If the slope CSV is available, the first slope x-coordinate is mapped
        to the start of the ParaPy slope at x = waterway.d_slope. This keeps
        the imported CFD points aligned with the waterway geometry.
        """
        df_slope = self._read_velocity_csv(self.slope_velocity_csv)

        if df_slope is None or df_slope.empty or "x" not in df_slope.columns:
            return 0.0

        return float(df_slope["x"].min() - self.waterway.d_slope)

    # ---------------------------------------------------------------------------------
    # Helper functions to generate a 3D geometry in case the CFD is run for a 3D case
    # ---------------------------------------------------------------------------------
    @ppc.Attribute
    def is_3d_geometry(self):
        return self.openfoam_simulation_type.upper() == "3D"

    @ppc.Attribute
    def cfd_left_boundary_to_propeller(self):
        if self.is_3d_geometry:
            return self.cfd_left_boundary_to_propeller_3d
        return self.cfd_left_boundary_to_propeller_2d

    @ppc.Attribute
    def gui_domain_width(self):
        if self.is_3d_geometry:
            return self.cfd_domain_width_3d
        return 0.0

    @ppc.Attribute
    def propeller_box_y_length(self):
        return 0.4

    @ppc.Attribute
    def propeller_y_position(self):
        if self.is_3d_geometry:
            return 0.5 * self.cfd_domain_width_3d - 0.5 * self.propeller_box_y_length
        else:
            return -0.2

    @ppc.Attribute
    def ship_box_y_length(self):
        return 0.4

    @ppc.Attribute
    def ship_y_position(self):
        if self.is_3d_geometry:
            return 0.5 * self.cfd_domain_width_3d - 0.5 * self.ship_box_y_length
        else:
            return -0.2

    @ppc.Attribute
    def propeller_disk_thickness(self):
        """Visual thickness of the circular propeller disk in 3D. [m]"""
        return 0.2

class VelocityFieldVisualization(ppc.Base):
    """Visualize post-processed CFD velocity samples in the ParaPy GUI.

    The class reads one or more CSV files containing CFD sample points and
    displays them as a coloured point cloud. The intention is to provide a
    ParaView-like engineering overview inside ParaPy, without embedding
    ParaView itself.

    Expected CSV columns:
        x, y, z, U_magnitude
    """

    csv_files = ppc.Input(
        [],
        doc="List of CFD CSV files containing x, y, z, U_magnitude columns."
    )

    waterway = ppc.Input(
        doc="Waterway object, used to map CFD coordinates to GUI coordinates."
    )

    cfd_x_offset = ppc.Input(
        0.0,
        doc="Offset between CFD x-coordinates and ParaPy GUI x-coordinates."
    )

    max_points = ppc.Input(
        300,
        doc="Maximum number of CFD points displayed in the GUI."
    )

    point_radius = ppc.Input(
        0.05,
        doc="Radius of each velocity point in the GUI."
    )

    show = ppc.Input(
        True,
        doc="Show or hide the CFD velocity field visualization."
    )

    red_ratio = ppc.Input(
        0.85,
        doc="Velocity/max_velocity ratio from which points are coloured red."
    )

    orange_ratio = ppc.Input(
        0.65,
        doc="Velocity/max_velocity ratio from which points are coloured orange."
    )

    yellow_ratio = ppc.Input(
        0.30,
        doc="Velocity/max_velocity ratio from which points are coloured yellow."
    )

    @ppc.Attribute
    def raw_velocity_dataframe(self):
        """Read and combine all available CFD velocity CSV files."""
        dataframes = []
        required_columns = {"x", "y", "z", "U_magnitude"}

        for filename in self.csv_files:
            if filename is None:
                continue

            if not os.path.exists(filename):
                print(f"CSV file not found: {filename}")
                continue

            df = pd.read_csv(filename)
            missing = required_columns - set(df.columns)

            if missing:
                raise ValueError(
                    f"Velocity CSV {filename} misses columns: {missing}"
                )

            dataframes.append(df)

        if not dataframes:
            return pd.DataFrame(columns=list(required_columns))

        return pd.concat(dataframes, ignore_index=True)

    @ppc.Attribute
    def sampled_velocity_dataframe(self):
        """Reduce the number of displayed points while keeping the maximum."""
        df = self.raw_velocity_dataframe

        if df.empty:
            return df

        df = df.sort_values(["x", "z", "y"]).reset_index(drop=True)

        if len(df) <= self.max_points:
            sampled = df.copy()
        else:
            indices = [
                round(i * (len(df) - 1) / (self.max_points - 1))
                for i in range(self.max_points)
            ]
            sampled = df.iloc[indices].copy()

        max_index = df["U_magnitude"].idxmax()
        max_row = df.loc[max_index]

        already_included = (
            (sampled["x"] == max_row["x"])
            & (sampled["y"] == max_row["y"])
            & (sampled["z"] == max_row["z"])
        ).any()

        if not already_included:
            sampled = pd.concat([sampled, max_row.to_frame().T])

        return sampled.reset_index(drop=True)

    @ppc.Attribute
    def velocity_data(self):
        """CFD velocity samples converted to dictionaries for ParaPy Parts."""
        return self.sampled_velocity_dataframe.to_dict("records")

    @ppc.Attribute
    def max_velocity(self):
        """Maximum velocity magnitude in the imported CFD field."""
        if not self.velocity_data:
            return 0.0

        return max(float(row["U_magnitude"]) for row in self.velocity_data)

    def _velocity_ratio(self, velocity):
        """Return velocity normalized with the maximum imported velocity."""
        if self.max_velocity == 0:
            return 0.0

        return float(velocity) / self.max_velocity

    def _velocity_color(self, velocity):
        """Map velocity magnitude to a simple green-yellow-orange-red scale."""
        ratio = self._velocity_ratio(velocity)

        if ratio >= self.red_ratio:
            return "red"
        if ratio >= self.orange_ratio:
            return "orange"
        if ratio >= self.yellow_ratio:
            return "yellow"
        return "green"

    def _point_position(self, row):
        """Map CFD coordinates to the current ParaPy geometry coordinates."""
        return translate(
            XOY,
            "x", float(row["x"]) - self.cfd_x_offset,
            "y", float(row["y"]),
            "z", float(row["z"]) - self.waterway.h
        )

    @ppc.Part
    def velocity_points(self):
        """Coloured CFD velocity point cloud shown in the ParaPy GUI."""
        return Sphere(
            quantify=len(self.velocity_data),
            radius=self.point_radius,
            position=self._point_position(self.velocity_data[child.index]),
            color=self._velocity_color(
                self.velocity_data[child.index]["U_magnitude"]
            ),
            suppress=not self.show or len(self.velocity_data) == 0
        )

    @ppc.Attribute
    def velocity_table(self):
        """Readable CFD velocity values for the ParaPy property grid."""
        return [
            {
                "x_gui": round(float(row["x"]) - self.cfd_x_offset, 3),
                "y_gui": round(float(row["y"]), 3),
                "z_gui": round(float(row["z"]) - self.waterway.h, 3),
                "U_magnitude": round(float(row["U_magnitude"]), 4),
                "velocity_ratio": round(
                    self._velocity_ratio(row["U_magnitude"]),
                    3
                )
            }
            for row in self.velocity_data
        ]
