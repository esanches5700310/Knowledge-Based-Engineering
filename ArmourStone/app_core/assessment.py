### IMPORTS ###
# Standard library imports
import datetime
import os
import threading
import numpy as np
from parapy import core as ppc
from parapy.gui.widgets import wx

# Import core
from app_core.geometry import Geometry
from app_core.obj_armourstone import ArmourStone
from app_core.obj_inputs import Inputs
from app_core.obj_project import Project
from app_core.obj_ship import Ship
from app_core.obj_waterway import Waterway
from app_core.warning import warn

# Import CFD inputs and workflow
from input import (
    run_cfd,
    manual_velocity,
    openfoam_simulation_type,
    cfd_left_boundary_to_propeller_2d,
    cfd_left_boundary_to_propeller_3d,
    cfd_domain_width_3d,
    cfd_cells_flat_x_2d,
    cfd_cells_slope_x_2d,
    cfd_cells_z_2d,
    cfd_cells_flat_x_3d,
    cfd_cells_slope_x_3d,
    cfd_cells_y_3d,
    cfd_cells_z_3d,
)
from openfoam.cfd_interface import make_cfd_settings_from_kbe, run_openfoam_workflow

### CLASSES ###
# CFD settings and results classes to group related inputs and outputs for the GUI and report generation.
class CFDInputs(ppc.Base):
    """User-facing CFD and hydraulic settings."""
    run_cfd = ppc.Input(run_cfd, doc="If True, use CFD-derived velocity rather than manual velocity.")
    manual_velocity = ppc.Input(manual_velocity, doc="Backup/design velocity used when CFD is not run or while CFD is pending. [m/s]")
    _openfoam_simulation_type = ppc.Input(
        openfoam_simulation_type,
        doc="OpenFOAM simulation type. Choose '2D' or '3D'."
    )
    cfd_left_boundary_to_propeller_2d = ppc.Input(
        cfd_left_boundary_to_propeller_2d,
        doc="Distance from left boundary to propeller centre for the 2D CFD domain. [m]"
    )
    cfd_left_boundary_to_propeller_3d = ppc.Input(
        cfd_left_boundary_to_propeller_3d,
        doc="Distance from left boundary to propeller centre for the 3D CFD domain. [m]"
    )
    cfd_domain_width_3d = ppc.Input(
        cfd_domain_width_3d,
        doc="Width of the 3D CFD domain. [m]"
    )
    cfd_cells_flat_x_2d = ppc.Input(cfd_cells_flat_x_2d, doc="Cell count along the flat bed in 2D CFD.")
    cfd_cells_slope_x_2d = ppc.Input(cfd_cells_slope_x_2d, doc="Cell count along the slope in 2D CFD.")
    cfd_cells_z_2d = ppc.Input(cfd_cells_z_2d, doc="Vertical cell count in 2D CFD.")
    cfd_cells_flat_x_3d = ppc.Input(cfd_cells_flat_x_3d, doc="Cell count along the flat bed in 3D CFD.")
    cfd_cells_slope_x_3d = ppc.Input(cfd_cells_slope_x_3d, doc="Cell count along the slope in 3D CFD.")
    cfd_cells_y_3d = ppc.Input(cfd_cells_y_3d, doc="Spanwise cell count in 3D CFD.")
    cfd_cells_z_3d = ppc.Input(cfd_cells_z_3d, doc="Vertical cell count in 3D CFD.")

    @ppc.Attribute
    def openfoam_simulation_type(self):
        """Validate the OpenFOAM simulation type input."""
        value = self._openfoam_simulation_type.strip().upper()
        if value not in {"2D", "3D"}:
            warn("Invalid simulation type", "Invalid OpenFOAM simulation type. Choose '2D' or '3D'.")
            raise ValueError("Invalid OpenFOAM simulation type. Choose '2D' or '3D'.")
        return value

# Grouped output class for GUI results display.
class AssessmentResults(ppc.Base):
    """Grouped output values for the GUI results section."""
    assessment = ppc.Input()

    @ppc.Attribute
    def required_D_n50(self):
        value = self.assessment.required_D_n50
        return float(value) if value is not None else None

    @ppc.Attribute
    def required_D_n50_cm(self):
        value = self.assessment.required_D_n50_cm
        return float(value) if value is not None else None

    @ppc.Attribute
    def governing_velocity(self):
        value = self.assessment.hydraulic_velocity
        return float(value) if value is not None else None

    @ppc.Attribute
    def cfd_error(self):
        return self.assessment.cfd_error

    @ppc.Attribute
    def cfd_status_message(self):
        """Expose the CFD status message from the main assessment for the GUI results panel."""
        return self.assessment.cfd_status_message

# Main assessment class that ties together all components and logic.
class ArmourStoneAssessment(ppc.Base):
    _cfd_result = None
    _cfd_thread = None
    cfd_running_flag = ppc.Input(False, doc="Internal CFD running indicator.")

    @ppc.Part
    def project(self):
        return Project()
    
    @ppc.Part
    def inputs(self):
        return Inputs()

    @ppc.Part
    def ship(self):
        return Ship(inputs=self.inputs)

    @ppc.Part
    def waterway(self):
        return Waterway(inputs=self.inputs)

    @ppc.Part
    def armourStone(self):
        return ArmourStone(inputs=self.inputs)

    @ppc.Part
    def results(self):
        return AssessmentResults(assessment=self)

    @ppc.Part
    def cfd(self):
        return CFDInputs()

    @ppc.Attribute(settable=True)
    def cfd_result(self):
        return self._cfd_result

    @ppc.action
    def run_cfd_simulation(self):
        """Start the CFD workflow when the button is pressed."""
        if not self.cfd.run_cfd:
            self._invalidate_dependants()
            return

        self.cfd_result = None
        self.evaluate_all(max_depth=1)
        self._start_cfd_thread()
        self._invalidate_dependants()

    def _run_cfd_workflow(self):
        try:
            settings = self.cfd_settings
            summary = run_openfoam_workflow(settings)
            self.cfd_result = summary
        except Exception as exc:
            self.cfd_result = {
                "latest_time": None,
                "max_flat_bed_velocity": None,
                "max_slope_velocity": None,
                "governing_velocity": self.cfd.manual_velocity,
                "error": str(exc),
            }
        finally:
            # Mark CFD as finished and refresh dependants.
            self.cfd_running_flag = False
            try:
                if hasattr(self, "results") and self.results is not None:
                    wx.CallAfter(self.results.invalidate_dependants, "cfd_status_message")
            except Exception:
                pass
            try:
                wx.CallAfter(self.invalidate_dependants, "cfd_running")
                wx.CallAfter(self.invalidate_dependants, "cfd_status_message")
            except Exception:
                try:
                    self.invalidate_dependants("cfd_running")
                    self.invalidate_dependants("cfd_status_message")
                except Exception:
                    pass
            # Also refresh standard dependants
            self._invalidate_dependants()

    def _invalidate_dependants(self):
        for attr in [
            "cfd_error",
            "cfd_summary",
            "hydraulic_velocity",
            "required_D_n50",
            "required_D_n50_cm",
        ]:
            try:
                self.invalidate_dependants(attr)
            except Exception:
                pass
            try:
                wx.CallAfter(self.invalidate_dependants, attr)
            except Exception:
                pass

        if hasattr(self, "results") and self.results is not None:
            for attr in [
                "required_D_n50",
                "required_D_n50_cm",
                "governing_velocity",
                "cfd_error",
            ]:
                try:
                    self.results.invalidate_dependants(attr)
                except Exception:
                    pass
                try:
                    wx.CallAfter(self.results.invalidate_dependants, attr)
                except Exception:
                    pass

    def _start_cfd_thread(self):
        if self._cfd_thread is None or not self._cfd_thread.is_alive():
            # Set running flag immediately so the GUI can update instantly.
            self.cfd_running_flag = True
            try:
                if hasattr(self, "results") and self.results is not None:
                    wx.CallAfter(self.results.invalidate_dependants, "cfd_status_message")
            except Exception:
                pass
            try:
                wx.CallAfter(self.invalidate_dependants, "cfd_running")
                wx.CallAfter(self.invalidate_dependants, "cfd_status_message")
            except Exception:
                try:
                    self.invalidate_dependants("cfd_running")
                    self.invalidate_dependants("cfd_status_message")
                except Exception:
                    pass

            self._cfd_thread = threading.Thread(target=self._run_cfd_workflow, daemon=True)
            self._cfd_thread.start()

    @ppc.Attribute
    def cfd_case_name(self):
        """Generate a unique CFD case name from the project name, project number and simulation type."""
        simulation_type = self.cfd.openfoam_simulation_type.upper()

        return (
            f"case_"
            f"{self.project.project_name}_"
            f"{self.project.project_nr}_"
            f"{simulation_type}"
        )

    @ppc.Attribute
    def cfd_running(self):
        """Boolean indicating whether the CFD thread is currently running."""
        return bool(self.cfd_running_flag or (self._cfd_thread is not None and self._cfd_thread.is_alive()))

    @ppc.Attribute
    def cfd_status_message(self):
        """Readable CFD status for the GUI."""
        if not self.cfd.run_cfd:
            return "CFD disabled"
        if self.cfd_running:
            return "Running"
        if self.cfd_result is None:
            return "Pending"
        if self.cfd_result and self.cfd_result.get("error"):
            warn("CFD error", f"Error in CFD run: {self.cfd_result.get('error')}")
            return f"Error: {self.cfd_result.get('error')}"
        return "Completed"

    @ppc.Attribute
    def delta(self):
        """
        Calculate the relative buoyant density of the protection element.

        :return: Relative buoyant density of the protection element. [-]
        """
        return self.armourStone.density_rock / self.armourStone.density_water - 1
    
    @ppc.Attribute
    def k_h(self):
        """
        Calculate the velocity profile factor.

        :return: Velocity profile factor. [-]
        """
        return 2 / (np.log(1 + 12 * self.waterway.h / self.armourStone.k_s)**2)
    
    @ppc.Attribute
    def k_sl(self):
        """
        Calculate the side slope factor.

        :return: Side slope factor. [-]
        """
        return (np.cos(self.waterway.psi_flow_rad) * np.sin(self.waterway.beta_rad) + np.sqrt(np.cos(self.waterway.beta_rad)**2 * np.tan(self.waterway.phi_as_rad)**2 - np.sin(self.waterway.psi_flow_rad)**2 * np.sin(self.waterway.beta_rad)**2)) / np.tan(self.waterway.phi_as_rad)

    @ppc.Attribute
    def pilarczyk(self):
        """
        Calculate the required stone diameter according to Pilarczyk (1995).

        :param phi_sc: Stability correction factor. [-]
        :param delta: Relative buoyant density of the protection element. [-]
        :param psi_cr: Critical mobility parameter of the protection element. [-]
        :param k_h: Velocity profile factor. [-]
        :param k_sl: Side slope factor. [-]
        :param k_t2: Square of the turbulence factor. [-]
        :param U: Depth-averaged flow velocity. [m/s]
        :return: Characteristic size of the protection element [m]. D = D_n50 for armourstone.
        """
        if self.hydraulic_velocity is None:
            return None

        g = 9.80665  # Acceleration due to gravity [m/s^2]

        # Calculate the required stone diameter using Pilarczyk's formula
        D = self.armourStone.phi_sc / self.delta * 0.035 / self.armourStone.psi_cr * self.k_h * self.k_sl**(-1) * self.armourStone.k_t2**2 * self.hydraulic_velocity**2**2 / (2 * g)
        return D

    @ppc.Part
    def geom(self):
        return Geometry(
            waterway=self.waterway,
            ship=self.ship,
            cfd_results_dir=self.cfd_results_dir,
            cfd_left_boundary_to_propeller_2d=self.cfd.cfd_left_boundary_to_propeller_2d,
            cfd_left_boundary_to_propeller_3d=self.cfd.cfd_left_boundary_to_propeller_3d,
            cfd_domain_width_3d=self.cfd.cfd_domain_width_3d,
            openfoam_simulation_type=self.cfd.openfoam_simulation_type
        )
    
    @ppc.action
    def report(self):
        """
        Generate and save the report on button press.
        """
        filename = "output/" + self.project.project_name + "_" + self.project.project_nr + "_report.pdf"

        if self.cfd.run_cfd:
            thread = self._cfd_thread
            if thread is None:
                warn("CFD not started", "CFD is enabled but has not been started. Run CFD before generating a report.")
                raise RuntimeError("CFD is enabled but has not been started. Run CFD before generating a report.")
            if thread.is_alive():
                thread.join()
            if self.cfd_result is None:
                warn("CFD incomplete", "CFD did not complete successfully. Check the CFD run before generating a report.")
                raise RuntimeError("CFD did not complete successfully. Check the CFD run before generating a report.")

        inputs = self._report_inputs()
        details = self._report_details()
        summary = self._report_summary()
        text = self._format_report_text(inputs, details, summary)

        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages
        from matplotlib.patches import Polygon as MplPolygon

        fig = plt.figure(figsize=(11.7, 8.3))
        ax_text = fig.add_subplot(1, 2, 1)
        ax_geom = fig.add_subplot(1, 2, 2)

        ax_text.axis("off")
        ax_text.text(
            0,
            1,
            text,
            va="top",
            ha="left",
            family="monospace",
            fontsize=8,
            wrap=True,
        )

        self._draw_geometry(ax_geom)

        with PdfPages(filename) as pdf:
            pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        return filename

    def _report_inputs(self):
        return {
            "Ship": {
                "Propeller diameter (D_p) [m]": self.ship.D_p,
                "Propeller vertical position (Z_p) [m]": self.ship.Z_p,
                "Hull draught [m]": self.ship.draught,
                "Jet velocity [m/s]": self.ship.jet_velocity,
            },
            "Waterway": {
                "Water depth h [m]": self.waterway.h,
                "Propeller-to-slope distance [m]": self.waterway.d_slope,
                "Slope angle beta [deg]": self.waterway.beta,
                "Armourstone repose angle phi_as [deg]": self.waterway.phi_as,
                "Flow direction psi_flow [deg]": self.waterway.psi_flow,
            },
            "ArmourStone": {
                "Rock density [kg/m^3]": self.armourStone.density_rock,
                "Water density [kg/m^3]": self.armourStone.density_water,
                "Critical mobility psi_cr [-]": self.armourStone.psi_cr,
                "Stability correction phi_sc [-]": self.armourStone.phi_sc,
                "Turbulence factor k_t2 [-]": self.armourStone.k_t2,
                "Roughness height k_s [m]": self.armourStone.k_s,
                "Manual hydraulic velocity [m/s]": self.cfd.manual_velocity,
            },
            "CFD": {
                "Use CFD": self.cfd.run_cfd,
                "Simulation type": self.cfd.openfoam_simulation_type,
                "Left boundary to propeller 2D [m]": self.cfd.cfd_left_boundary_to_propeller_2d,
                "Left boundary to propeller 3D [m]": self.cfd.cfd_left_boundary_to_propeller_3d,
                "Domain width 3D [m]": self.cfd.cfd_domain_width_3d,
                "Cells flat x 2D": self.cfd.cfd_cells_flat_x_2d,
                "Cells slope x 2D": self.cfd.cfd_cells_slope_x_2d,
                "Cells z 2D": self.cfd.cfd_cells_z_2d,
                "Cells flat x 3D": self.cfd.cfd_cells_flat_x_3d,
                "Cells slope x 3D": self.cfd.cfd_cells_slope_x_3d,
                "Cells y 3D": self.cfd.cfd_cells_y_3d,
                "Cells z 3D": self.cfd.cfd_cells_z_3d,
            },
        }

    def _report_details(self):
        return {
            "Derived parameters": {
                "Relative buoyant density delta [-]": self.delta,
                "Velocity profile factor k_h [-]": self.k_h,
                "Side slope factor k_sl [-]": self.k_sl,
                "Hydraulic velocity [m/s]": self.hydraulic_velocity,
                "Required D_n50 [m]": self.required_D_n50,
                "Required D_n50 [cm]": self.required_D_n50_cm,
            },
            "CFD results": {
                "Latest time [s]": self.cfd_summary["latest_time"],
                "Max flat bed velocity [m/s]": self.cfd_summary["max_flat_bed_velocity"],
                "Max slope velocity [m/s]": self.cfd_summary["max_slope_velocity"],
                "Governing velocity [m/s]": self.cfd_summary["governing_velocity"],
            },
        }

    def _report_summary(self):
        return {
            "Report generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Main output": {
                "Required D_n50 [m]": self.required_D_n50,
                "Required D_n50 [cm]": self.required_D_n50_cm,
            },
        }

    def _format_report_text(self, inputs, details, summary):
        lines = [
            "ArmourStone Assessment Report",
            "===========================",
            f"Generated: {summary['Report generated']}",
            "",
        ]

        for section, values in inputs.items():
            lines.append(section)
            lines.append("-" * len(section))
            for label, value in values.items():
                lines.append(f"{label}: {self._format_value(value)}")
            lines.append("")

        for section, values in details.items():
            lines.append(section)
            lines.append("-" * len(section))
            for label, value in values.items():
                lines.append(f"{label}: {self._format_value(value)}")
            lines.append("")

        lines.append("Summary")
        lines.append("-------")
        for label, value in summary["Main output"].items():
            lines.append(f"{label}: {self._format_value(value)}")
        lines.append("")
        return "\n".join(lines)

    def _format_value(self, value):
        if value is None:
            return "n/a"
        if isinstance(value, bool):
            return str(value)
        if isinstance(value, (int, float)):
            return f"{value:.4f}" if isinstance(value, float) else str(value)
        return str(value)

    def _draw_geometry(self, ax):
        from matplotlib.patches import Polygon as MplPolygon

        h = self.waterway.h
        d_slope = self.waterway.d_slope
        width = self.waterway.waterway_width
        xbed = [0.0, d_slope, d_slope + width]
        zbed = [-h, -h, 0.0]

        ax.plot([0.0, xbed[-1]], [0.0, 0.0], color="blue", lw=2)
        ax.plot(xbed, zbed, color="blue", lw=2)

        water_poly = MplPolygon(
            [(0.0, 0.0), (0.0, -h), (d_slope, -h), (d_slope + width, 0.0)],
            closed=True,
            facecolor="lightskyblue",
            edgecolor="none",
            alpha=0.3,
        )
        ax.add_patch(water_poly)

        ship = MplPolygon(
            [(-2.0, 0.0), (-2.0, -self.ship.draught), (-0.1, -self.ship.draught), (-0.1, 0.0)],
            closed=True,
            facecolor="black",
            alpha=0.5,
        )
        ax.add_patch(ship)

        prop_top = -h + self.ship.Z_p + self.ship.D_p / 2
        prop_bottom = -h + self.ship.Z_p - self.ship.D_p / 2
        prop = MplPolygon(
            [(-0.1, prop_top), (-0.1, prop_bottom), (0.0, prop_bottom), (0.0, prop_top)],
            closed=True,
            facecolor="red",
            alpha=0.7,
        )
        ax.add_patch(prop)

        ax.set_title("Geometry sketch")
        ax.set_xlabel("x [m]")
        ax.set_ylabel("z [m]")
        ax.set_aspect("equal", adjustable="box")
        ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.5)
        ax.set_xlim(-2.5, max(d_slope + width, 5.0))
        ax.set_ylim(-max(h, 5.0), 1.0)

    @ppc.Attribute
    def cfd_settings(self):
        """Create the CFD settings from the KBE model inputs."""
        return make_cfd_settings_from_kbe(
            ship=self.ship,
            waterway=self.waterway,
            jet_velocity=self.ship.jet_velocity,
            simulation_type=self.cfd.openfoam_simulation_type,
            case_name=self.cfd_case_name,
            propeller_to_slope_distance=self.waterway.d_slope,
            left_boundary_to_propeller_2d=self.cfd.cfd_left_boundary_to_propeller_2d,
            left_boundary_to_propeller_3d=self.cfd.cfd_left_boundary_to_propeller_3d,
            domain_width_3d=self.cfd.cfd_domain_width_3d,
            cells_flat_x_2d=self.cfd.cfd_cells_flat_x_2d,
            cells_slope_x_2d=self.cfd.cfd_cells_slope_x_2d,
            cells_z_2d=self.cfd.cfd_cells_z_2d,
            cells_flat_x_3d=self.cfd.cfd_cells_flat_x_3d,
            cells_slope_x_3d=self.cfd.cfd_cells_slope_x_3d,
            cells_y_3d=self.cfd.cfd_cells_y_3d,
            cells_z_3d=self.cfd.cfd_cells_z_3d,
        )

    @ppc.Attribute
    def cfd_summary(self):
        """Return cached CFD results or a placeholder if CFD has not finished."""
        if not self.cfd.run_cfd:
            return {
                "latest_time": None,
                "max_flat_bed_velocity": None,
                "max_slope_velocity": None,
                "governing_velocity": self.cfd.manual_velocity,
            }

        if self.cfd_result is None:
            return {
                "latest_time": None,
                "max_flat_bed_velocity": None,
                "max_slope_velocity": None,
                "governing_velocity": None,
            }

        return self.cfd_result

    @ppc.Attribute
    def hydraulic_velocity(self):
        """Velocity used in the armour-stone calculation.

        If run_cfd is False, use manual_velocity.
        If run_cfd is True, wait until CFD completes before using CFD velocity.
        """
        if self.cfd.run_cfd:
            if self.cfd_result is None:
                return None
            return self.cfd_summary["governing_velocity"]

        return self.cfd.manual_velocity

    @ppc.Attribute
    def cfd_error(self):
        return self.cfd_result.get("error") if self.cfd_result else None

    @ppc.Attribute
    def required_D_n50(self):
        """Required nominal armour stone diameter. [m]"""
        if self.pilarczyk is None:
            return None
        return float(self.pilarczyk)

    @ppc.Attribute
    def required_D_n50_cm(self):
        """Required nominal armour stone diameter. [cm]"""
        if self.required_D_n50 is None:
            return None
        return float(100 * self.required_D_n50)

    @ppc.Attribute
    def armourstone_dir(self):
        return os.path.dirname(os.path.abspath(__file__))

    @ppc.Attribute
    def cfd_results_dir(self):
        return os.path.join(
            self.armourstone_dir,
            "output",
            "cfd_results",
            self.cfd_case_name
        )