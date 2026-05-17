import threading
import warnings
import numpy as np
from parapy import core as ppc
from parapy.core.exceptions import ParaPyDeprecationWarning
from parapy.gui import display
from parapy.gui.widgets import wx
from objects import Ship, Waterway, ArmourStone
from geometry import Geometry
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

class CFDInputs(ppc.Base):
    """User-facing CFD and hydraulic settings."""
    run_cfd = ppc.Input(run_cfd, doc="If True, use CFD-derived velocity rather than manual velocity.")
    manual_velocity = ppc.Input(manual_velocity, doc="Backup/design velocity used when CFD is not run or while CFD is pending. [m/s]")
    openfoam_simulation_type = ppc.Input(
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
    def required_D_n50_note(self):
        return self.assessment.required_D_n50_note

    @ppc.Attribute
    def cfd_feedback(self):
        if self.cfd_error:
            return f"CFD error: {self.cfd_error}"

        status = self.assessment.cfd_status
        if status == "idle":
            return "CFD has not been started. Press the Run CFD button."
        if status == "disabled":
            return "CFD is disabled. Enable CFD before pressing Run CFD."
        if status == "queued":
            return "CFD is queued and will begin shortly."
        if status == "creating case":
            return "Creating the CFD case files."
        if status == "running OpenFOAM":
            return "OpenFOAM is running. This can take several minutes."
        if status == "postprocessing":
            return "Postprocessing CFD results."
        if status == "done":
            return "CFD is complete. Results are ready."
        return f"CFD status: {status}"


class ArmourStoneAssessment(ppc.Base):
    _cfd_status = "idle"
    _cfd_progress = 0
    _cfd_result = None
    _cfd_thread = None

    @ppc.Attribute(settable=True)
    def cfd_result(self):
        return self._cfd_result

    @ppc.Part
    def ship(self):
        return Ship()

    @ppc.Part
    def waterway(self):
        return Waterway()

    @ppc.Part
    def armourStone(self):
        return ArmourStone()

    @ppc.Part
    def results(self):
        return AssessmentResults(assessment=self)

    @ppc.Part
    def cfd(self):
        return CFDInputs()

    @ppc.action
    def run_cfd_simulation(self):
        """Start the CFD workflow when the button is pressed."""
        if not self.cfd.run_cfd:
            self._set_cfd_status("disabled", 0)
            return

        self.cfd_result = None
        self._set_cfd_status("queued", 1)
        self.evaluate_all(max_depth=1)
        self._start_cfd_thread()

    def _set_cfd_status(self, status, progress=0):
        self.cfd_status = status
        self.cfd_progress = progress
        for attr in ["cfd_status", "cfd_progress"]:
            try:
                self.invalidate_dependants(attr)
            except Exception:
                pass
            try:
                wx.CallAfter(self.invalidate_dependants, attr)
            except Exception:
                pass

        if hasattr(self, "results") and self.results is not None:
            for attr in ["cfd_feedback"]:
                try:
                    self.results.invalidate_dependants(attr)
                except Exception:
                    pass
                try:
                    wx.CallAfter(self.results.invalidate_dependants, attr)
                except Exception:
                    pass

    def _run_cfd_workflow(self):
        try:
            self._set_cfd_status("creating case", 20)
            settings = self.cfd_settings
            self._set_cfd_status("running OpenFOAM", 50)
            summary = run_openfoam_workflow(settings)
            self._set_cfd_status("postprocessing", 80)
            self.cfd_result = summary
            self._set_cfd_status("done", 100)
        except Exception as exc:
            self.cfd_result = {
                "latest_time": None,
                "max_flat_bed_velocity": None,
                "max_slope_velocity": None,
                "governing_velocity": self.cfd.manual_velocity,
                "error": str(exc),
            }
            self._set_cfd_status(f"error: {exc}", 100)
        finally:
            self._invalidate_dependants()

    def _invalidate_dependants(self):
        for attr in [
            "cfd_status",
            "cfd_progress",
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
                "cfd_feedback",
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
            self._cfd_thread = threading.Thread(target=self._run_cfd_workflow, daemon=True)
            self._cfd_thread.start()

    @ppc.Attribute(settable=True)
    def cfd_status(self):
        return self._cfd_status

    @ppc.Attribute(settable=True)
    def cfd_progress(self):
        return self._cfd_progress

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
        return Geometry(waterway=self.waterway, ship=self.ship)
    
    def report(self):
        """
        Generate and save the report.
        """
        pass

    def run(self):
        """Run the assessment and print the main results."""

        print("Running armour stone assessment")
        print("-------------------------------")
        print(f"Run CFD: {self.cfd.run_cfd}")
        print(f"OpenFOAM simulation type: {self.cfd.openfoam_simulation_type}")
        print(f"Hydraulic velocity used: {self.hydraulic_velocity:.4f} m/s")
        print(f"Required D_n50: {self.required_D_n50:.4f} m")

        if self.cfd.run_cfd:
            print()
            print("CFD settings")
            print("------------")
            print(f"Case name: {self.cfd_settings.case_name}")
            print(f"Propeller to slope distance: {self.waterway.d_slope:.2f} m")
            print(f"Flat bed length: {self.cfd_settings.flat_bed_length:.2f} m")
            print(f"Domain width: {self.cfd_settings.domain_width:.2f} m")
            print(f"Simulation type: {self.cfd_settings.simulation_type}")

            print()
            print("CFD results")
            print("-----------")
            print(f"Latest time: {self.cfd_summary['latest_time']}")
            print(f"Max flat bed velocity: {self.cfd_summary['max_flat_bed_velocity']:.4f} m/s")
            print(f"Max slope velocity: {self.cfd_summary['max_slope_velocity']:.4f} m/s")
            print(f"Governing velocity: {self.cfd_summary['governing_velocity']:.4f} m/s")

    @ppc.Attribute
    def cfd_settings(self):
        """Create the CFD settings from the KBE model inputs."""
        return make_cfd_settings_from_kbe(
            ship=self.ship,
            waterway=self.waterway,
            jet_velocity=self.ship.jet_velocity,
            simulation_type=self.cfd.openfoam_simulation_type,
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
    def required_D_n50_note(self):
        if self.cfd.run_cfd and self.cfd_result is None:
            return "CFD is still running, so D_n50 is unavailable until CFD completes."
        if self.cfd.run_cfd and self.cfd_result is not None:
            return "D_n50 is based on CFD-derived governing velocity."
        return "D_n50 is based on manual velocity because CFD is disabled."

if __name__ == "__main__":
    app = ArmourStoneAssessment()
    app.evaluate_all(max_depth=1)
    display(app, view="front", autodraw=True)
