import os
import pandas as pd

from parapy import core as ppc
from parapy.core import child
from parapy.geom import Polygon, Sphere, Point, TextLabel, Box, translate, XOY

class Geometry(ppc.Base):

    waterway = ppc.Input()
    ship = ppc.Input()

    cfd_left_boundary_to_propeller_2d = ppc.Input(
        0.0,
        doc="Distance from the left CFD boundary to the propeller for the 2D case."
    )

    cfd_results_dir = ppc.Input(
        None,
        doc="Folder containing the CFD CSV result files."
    )

    @ppc.Attribute
    def flat_bed_velocity_csv(self):
        if self.cfd_results_dir is None:
            return None

        return os.path.join(
            self.cfd_results_dir,
            "flat_bed_velocity_samples.csv"
        )

    @ppc.Attribute
    def slope_velocity_csv(self):
        if self.cfd_results_dir is None:
            return None

        return os.path.join(
            self.cfd_results_dir,
            "slope_velocity_samples.csv"
        )

    n_velocity_markers = ppc.Input(
        10,
        doc="Number of velocity markers to show on flat bed and slope."
    )

    show_velocity_markers = ppc.Input(
        True,
        doc="Show CFD velocity sample markers in the geometry view."
    )

    show_velocity_labels = ppc.Input(
        True,
        doc="Show velocity value labels next to the markers."
    )

    velocity_label_size = ppc.Input(
        0.2,
        doc="Size of the velocity text labels."
    )

    slope_label_y_offset = ppc.Input(
        -0.6,
        doc="Y-offset used to move slope labels away from slope velocity markers."
    )

    flat_bed_label_y_offset = ppc.Input(
        -0.6,
        doc="Y-offset used to move flat bed labels away from flat bed velocity markers."
    )

    def _child_index(self, index):
        """Return a normal integer index from ParaPy child.index."""
        if isinstance(index, list):
            return index[-1]

        if isinstance(index, tuple):
            return index[-1]

        return index

    def _marker_radius(self, data, max_velocity, index):
        """Return marker radius for one marker."""
        i = self._child_index(index)
        row = data[i]

        return 0.15 if row["U_magnitude"] == max_velocity else 0.10

    def _marker_color(self, data, max_velocity, index, normal_color=None):
        """Return marker color based on relative velocity magnitude."""
        if not data or max_velocity in [None, 0]:
            return "green"

        i = self._child_index(index)
        row = data[i]

        velocity = float(row["U_magnitude"])
        velocity_ratio = velocity / max_velocity

        if velocity_ratio >= 0.95:
            return "red"  # highest / near-highest
        elif velocity_ratio >= 0.65:
            return "orange"  # high
        elif velocity_ratio >= 0.30:
            return "yellow"  # intermediate
        else:
            return "green"  # low

    def _marker_position(self, data, index, y_offset):
        """Return marker position for one marker."""
        i = self._child_index(index)
        row = data[i]

        return self._to_gui_point(row, y_offset=y_offset)

    @ppc.Part
    def flat_bed_velocity_labels(self):
        return TextLabel(
            quantify=len(self.flat_bed_velocity_data),
            text="{:.2f} m/s".format(
                self.flat_bed_velocity_data[child.index]["U_magnitude"]
            ),
            position=self._marker_position(
                self.flat_bed_velocity_data,
                child.index,
                y_offset=self.flat_bed_label_y_offset
            ),
            size=self.velocity_label_size,
            color="black",
            suppress=not self.show_velocity_labels
        )

    @ppc.Part
    def slope_velocity_labels(self):
        return TextLabel(
            quantify=len(self.slope_velocity_data),
            text="{:.2f} m/s".format(
                self.slope_velocity_data[child.index]["U_magnitude"]
            ),
            position=self._marker_position(
                self.slope_velocity_data,
                child.index,
                y_offset=self.slope_label_y_offset
            ),
            size=self.velocity_label_size,
            color="black",
            suppress=not self.show_velocity_labels
        )

    @ppc.Part
    def waterway_shape(self):
        return Polygon([
            (-self.cfd_left_boundary_to_propeller_2d, 0, -self.waterway.h),
            (self.waterway.d_slope, 0, -self.waterway.h),
            (self.waterway.d_slope + self.waterway.waterway_width, 0, 0),
            (-self.cfd_left_boundary_to_propeller_2d, 0, 0)
        ], color="blue")

    @ppc.Part
    def propeller_shape(self):
        return Box(
            width=0.2,
            length=0.4,
            height=self.ship.D_p,
            position=translate(
                XOY,
                "x", -0.2,
                "y", -0.2,
                "z", -self.waterway.h + self.ship.Z_p - self.ship.D_p / 2
            ),
            color="red"
        )

    @ppc.Part
    def ship_shape(self):
        return Box(
            width=1.9,
            length=0.4,
            height=self.ship.draught,
            position=translate(
                XOY,
                "x", -2.0,
                "y", -0.2,
                "z", -self.ship.draught
            ),
            color="black"
        )

    def _read_velocity_csv(self, filename):
        """Read a CFD velocity CSV file."""
        if filename is None:
            return None

        if not os.path.exists(filename):
            print(f"CSV file not found: {filename}")
            return None

        df = pd.read_csv(filename)

        required_columns = {"x", "y", "z", "U_magnitude"}
        missing = required_columns - set(df.columns)

        if missing:
            raise ValueError(
                f"Velocity CSV {filename} misses columns: {missing}"
            )

        return df

    def _sample_velocity_points(self, df):
        """Return approximately n equally spaced samples plus the max point."""
        if df is None or df.empty:
            return []

        df = df.sort_values("x").reset_index(drop=True)

        if len(df) <= self.n_velocity_markers:
            sampled = df.copy()
        else:
            indices = [
                round(i * (len(df) - 1) / (self.n_velocity_markers - 1))
                for i in range(self.n_velocity_markers)
            ]
            sampled = df.iloc[indices].copy()

        max_index = df["U_magnitude"].idxmax()
        max_row = df.loc[max_index]

        # Make sure the max point is included, even if it was not selected
        # by the equally spaced sampling.
        if not ((sampled["x"] == max_row["x"]) &
                (sampled["z"] == max_row["z"])).any():
            sampled = pd.concat([sampled, max_row.to_frame().T])

        sampled = sampled.reset_index(drop=True)
        return sampled.to_dict("records")

    @ppc.Attribute
    def flat_bed_velocity_data(self):
        """Sampled flat bed velocity points."""
        df = self._read_velocity_csv(self.flat_bed_velocity_csv)
        return self._sample_velocity_points(df)

    @ppc.Attribute
    def slope_velocity_data(self):
        """Sample slope velocity points uniformly along the physical slope."""
        df = self._read_velocity_csv(self.slope_velocity_csv)

        if df is None or df.empty:
            return []

        df = df.copy()

        # Convert CFD coordinates to GUI coordinates
        df["x_gui"] = df["x"] - self.cfd_x_offset
        df["z_gui"] = df["z"] - self.waterway.h

        # Slope line in GUI coordinates:
        # start: bottom of slope
        # end: top of slope / water surface
        x0 = self.waterway.d_slope
        z0 = -self.waterway.h

        x1 = self.waterway.d_slope + self.waterway.waterway_width
        z1 = 0.0

        dx = x1 - x0
        dz = z1 - z0
        slope_length_squared = dx ** 2 + dz ** 2

        # Project every CFD point onto the slope direction.
        # This gives a coordinate from 0 to 1 along the slope.
        df["s_slope"] = (
                ((df["x_gui"] - x0) * dx + (df["z_gui"] - z0) * dz)
                / slope_length_squared
        )

        # Keep only points that are roughly on the actual slope range
        df = df[(df["s_slope"] >= 0.0) & (df["s_slope"] <= 1.0)]

        if df.empty:
            return []

        # Choose target locations uniformly along the slope
        targets = [
            i / (self.n_velocity_markers - 1)
            for i in range(self.n_velocity_markers)
        ]

        sampled_rows = []

        for target in targets:
            closest_index = (df["s_slope"] - target).abs().idxmin()
            sampled_rows.append(df.loc[closest_index])

        sampled = pd.DataFrame(sampled_rows).drop_duplicates(
            subset=["x", "z"]
        )

        # Always include the maximum velocity point as well
        max_index = df["U_magnitude"].idxmax()
        max_row = df.loc[max_index]

        if not ((sampled["x"] == max_row["x"]) &
                (sampled["z"] == max_row["z"])).any():
            sampled = pd.concat([sampled, max_row.to_frame().T])

        sampled = sampled.sort_values("s_slope").reset_index(drop=True)

        return sampled.to_dict("records")

    @ppc.Attribute
    def cfd_x_offset(self):
        """
        Offset between CFD x-coordinate and GUI x-coordinate.

        The first slope CSV point is mapped to the beginning of the
        ParaPy slope at x = waterway.d_slope.
        """
        df_slope = self._read_velocity_csv(self.slope_velocity_csv)

        if df_slope is None or df_slope.empty:
            return 0.0

        return float(df_slope["x"].min() - self.waterway.d_slope)

    def _to_gui_point(self, row, y_offset=0.0):
        """Convert a CFD CSV row to a ParaPy GUI point."""
        x_gui = float(row["x"]) - self.cfd_x_offset
        y_gui = y_offset
        z_gui = float(row["z"]) - self.waterway.h

        return Point(x_gui, y_gui, z_gui)

    @ppc.Attribute
    def max_flat_bed_velocity(self):
        if not self.flat_bed_velocity_data:
            return None
        return max(row["U_magnitude"] for row in self.flat_bed_velocity_data)

    @ppc.Attribute
    def max_slope_velocity(self):
        if not self.slope_velocity_data:
            return None
        return max(row["U_magnitude"] for row in self.slope_velocity_data)

    @ppc.Part
    def flat_bed_velocity_markers(self):
        return Sphere(
            quantify=len(self.flat_bed_velocity_data),
            radius=self._marker_radius(
                self.flat_bed_velocity_data,
                self.max_flat_bed_velocity,
                child.index
            ),
            position=self._marker_position(
                self.flat_bed_velocity_data,
                child.index,
                y_offset=0
            ),
            color=self._marker_color(
                self.flat_bed_velocity_data,
                self.max_flat_bed_velocity,
                child.index
            ),
            suppress=not self.show_velocity_markers
        )

    @ppc.Part
    def slope_velocity_markers(self):
        return Sphere(
            quantify=len(self.slope_velocity_data),
            radius=self._marker_radius(
                self.slope_velocity_data,
                self.max_slope_velocity,
                child.index
            ),
            position=self._marker_position(
                self.slope_velocity_data,
                child.index,
                y_offset=0
            ),
            color=self._marker_color(
                self.slope_velocity_data,
                self.max_slope_velocity,
                child.index
            ),
            suppress=not self.show_velocity_markers
        )

    @ppc.Attribute
    def flat_bed_velocity_table(self):
        """Readable velocity values for the ParaPy property grid."""
        return [
            {
                "x_gui": round(float(row["x"]) - self.cfd_x_offset, 3),
                "z_gui": round(float(row["z"]) - self.waterway.h, 3),
                "U_magnitude": round(float(row["U_magnitude"]), 4),
                "is_max": float(row["U_magnitude"]) == self.max_flat_bed_velocity
            }
            for row in self.flat_bed_velocity_data
        ]

    @ppc.Attribute
    def slope_velocity_table(self):
        """Readable velocity values for the ParaPy property grid."""
        return [
            {
                "x_gui": round(float(row["x"]) - self.cfd_x_offset, 3),
                "z_gui": round(float(row["z"]) - self.waterway.h, 3),
                "U_magnitude": round(float(row["U_magnitude"]), 4),
                "is_max": float(row["U_magnitude"]) == self.max_slope_velocity
            }
            for row in self.slope_velocity_data
        ]