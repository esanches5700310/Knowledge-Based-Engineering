import numpy as np
from parapy import core as ppc
from parapy.gui import display
from objects import Ship, Waterway, ArmourStone
from geometry import Geometry
from input import (
    run_cfd,
    manual_velocity,
    openfoam_simulation_type,
    propeller_to_slope_distance,
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

class ArmourStoneAssessment(ppc.Base):
    inputPath = ppc.Input("input.py", doc="Path to the input file containing the parameters for the assessment. [str]")
    run_cfd = ppc.Input(run_cfd, doc="If True, run OpenFOAM automatically.")
    manual_velocity = ppc.Input(manual_velocity, doc="Velocity used if OpenFOAM is not run. [m/s]")

    openfoam_simulation_type = ppc.Input(
        openfoam_simulation_type,
        doc="OpenFOAM simulation type. Choose '2D' or '3D'."
    )

    propeller_to_slope_distance = ppc.Input(
        propeller_to_slope_distance,
        doc="Distance from propeller centre to slope toe. Used for both 2D and 3D CFD. [m]"
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

    cfd_cells_flat_x_2d = ppc.Input(cfd_cells_flat_x_2d)
    cfd_cells_slope_x_2d = ppc.Input(cfd_cells_slope_x_2d)
    cfd_cells_z_2d = ppc.Input(cfd_cells_z_2d)

    cfd_cells_flat_x_3d = ppc.Input(cfd_cells_flat_x_3d)
    cfd_cells_slope_x_3d = ppc.Input(cfd_cells_slope_x_3d)
    cfd_cells_y_3d = ppc.Input(cfd_cells_y_3d)
    cfd_cells_z_3d = ppc.Input(cfd_cells_z_3d)

    @ppc.Part
    def ship(self):
        return Ship()

    @ppc.Part
    def waterway(self):
        return Waterway()

    @ppc.Part
    def armourStone(self):
        return ArmourStone()
    
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
        print(f"Run CFD: {self.run_cfd}")
        print(f"OpenFOAM simulation type: {self.openfoam_simulation_type}")
        print(f"Hydraulic velocity used: {self.hydraulic_velocity:.4f} m/s")
        print(f"Required D_n50: {self.required_D_n50:.4f} m")

        if self.run_cfd:
            print()
            print("CFD settings")
            print("------------")
            print(f"Case name: {self.cfd_settings.case_name}")
            print(f"Propeller to slope distance: {self.propeller_to_slope_distance:.2f} m")
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
            simulation_type=self.openfoam_simulation_type,
            propeller_to_slope_distance=self.propeller_to_slope_distance,
            left_boundary_to_propeller_2d=self.cfd_left_boundary_to_propeller_2d,
            left_boundary_to_propeller_3d=self.cfd_left_boundary_to_propeller_3d,
            domain_width_3d=self.cfd_domain_width_3d,
            cells_flat_x_2d=self.cfd_cells_flat_x_2d,
            cells_slope_x_2d=self.cfd_cells_slope_x_2d,
            cells_z_2d=self.cfd_cells_z_2d,
            cells_flat_x_3d=self.cfd_cells_flat_x_3d,
            cells_slope_x_3d=self.cfd_cells_slope_x_3d,
            cells_y_3d=self.cfd_cells_y_3d,
            cells_z_3d=self.cfd_cells_z_3d,
        )

    @ppc.Attribute
    def cfd_summary(self):
        """Run OpenFOAM and return the postprocessed CFD summary."""
        return run_openfoam_workflow(self.cfd_settings)

    @ppc.Attribute
    def hydraulic_velocity(self):
        """Velocity used in the armour-stone calculation.

        If run_cfd is False, use manual_velocity.
        If run_cfd is True, run OpenFOAM and use the governing CFD velocity.
        """
        if self.run_cfd:
            return self.cfd_summary["governing_velocity"]

        return self.manual_velocity

    @ppc.Attribute
    def required_D_n50(self):
        """Required nominal armour stone diameter. [m]"""
        return self.pilarczyk

    @ppc.Attribute
    def required_D_n50_cm(self):
        """Required nominal armour stone diameter. [cm]"""
        return 100 * self.required_D_n50

if __name__ == "__main__":
    test = ArmourStoneAssessment()
    test.run()
    display(test)
