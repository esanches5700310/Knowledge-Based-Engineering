import numpy as np
from parapy import core as ppc
import re
from input import *
from warning import warn

class Project(ppc.Base):

    input_project_name = ppc.Input(project_name, doc="Project name used for file and folder naming. Spaces are converted to underscores.")
    input_project_nr = ppc.Input(project_nr, doc="Project number used for file and folder naming. Spaces are converted to underscores.")

    @ppc.Attribute
    def project_name(self):
        """
        Fix project name and check validity.

        :return: Project name.
        """
        raw = self.input_project_name
        name = str(raw).strip()
        name = name.replace(" ", "_")
        # Remove special characters that would be invalid for a file/folder name
        name = re.sub(r"[^A-Za-z0-9_.-]", "", name)
        if not name:
            warn("Invalid project name", f"Name cannot be empty or only contain invalid characters. Please enter a valid name.")
            raise ValueError(f"Name cannot be empty or only contain invalid characters.")
        return name
    
    @ppc.Attribute
    def project_nr(self):
        """
        Check validity of project number.

        :return: Project number.
        """
        if not isinstance(self.input_project_nr, int):
            warn("Invalid project number", "Project number must be an integer. Please enter a valid project number.")
            raise ValueError("Project number must be an integer.")

        return self.input_project_nr

class Inputs(ppc.Base):
    """
    Class to do input handling and validation. Passes the validated inputs through to the other classes.
    """
    D_p = ppc.Input(D_p, doc="Diameter of the propeller. [m]")
    Z_p = ppc.Input(Z_p, doc="Propeller position, defined as the distance from the bed to the centre of the propeller. [m]")
    draught = ppc.Input(draught, doc="Distance from surface to lowest point of the hull. [m]")
    jet_velocity = ppc.Input(jet_velocity, doc="Target propeller jet velocity used in OpenFOAM. [m/s]")
    h = ppc.Input(depth, doc="Water depth. [m]")
    d_slope = ppc.Input(propeller_to_slope_distance, doc="Distance to slope. [m]")
    beta = ppc.Input(beta, doc="Side slope angle. [deg]")
    phi_as = ppc.Input(phi_as, doc="Angle of repose of the armourstone. [deg]")
    psi_flow = ppc.Input(psi_flow, doc="Angle made by the flow to the upslope direction. [deg]")

    @ppc.Attribute
    def _D_p(self):
        """Diameter of the propeller. [m]"""
        if self.D_p <= 0:
            warn("Invalid propeller diameter", "Diameter of the propeller must be a positive value. Please enter a valid diameter.")
            raise ValueError("Diameter of the propeller must be positive.")
            
        if self.D_p / 2 > self._Z_p:
            warn("Invalid propeller diameter", "Diameter of the propeller is too large for the given propeller position. Please enter a smaller diameter or adjust the propeller position.")
            raise ValueError("Diameter of the propeller is too large for the given propeller position.")
        return self.D_p
    
    @ppc.Attribute
    def _Z_p(self):
        """Propeller position, defined as the distance from the bed to the centre of the propeller. [m]"""
        if self.Z_p <= 0:
            warn("Invalid propeller position", "Propeller position must be a positive value. Please enter a valid propeller position.")
            raise ValueError("Propeller position must be positive.")
        return self.Z_p
    
    @ppc.Attribute
    def _draught(self):
        """Distance from surface to lowest point of the hull. [m]"""
        if self.draught <= 0:
            warn("Invalid draught", "Draught must be a positive value. Please enter a valid draught.")
            raise ValueError("Draught must be positive.")
        return self.draught
    
    @ppc.Attribute
    def _jet_velocity(self):
        """Target propeller jet velocity used in OpenFOAM. [m/s]"""
        if self.jet_velocity <= 0:
            warn("Invalid jet velocity", "Jet velocity must be a positive value. Please enter a valid jet velocity.")
            raise ValueError("Jet velocity must be positive.")
        return self.jet_velocity
    
    @ppc.Attribute
    def _h(self):
        """Water depth. [m]"""
        if self.h <= 0:
            warn("Invalid water depth", "Water depth must be a positive value. Please enter a valid water depth.")
            raise ValueError("Water depth must be positive.")
        if self.h < self._Z_p + self._D_p / 2:
            warn("Invalid water depth", "Water depth is too small for the given propeller position and diameter. Please enter a greater water depth or adjust the propeller position/diameter.")
            raise ValueError("Water depth is too small for the given propeller position and diameter.")
        return self.h
    
    @ppc.Attribute
    def _d_slope(self):
        """Distance to slope. [m]"""
        if self.d_slope <= 0:
            warn("Invalid distance to slope", "Distance to slope must be a positive value. Please enter a valid distance to slope.")
            raise ValueError("Distance to slope must be positive.")
        return self.d_slope
    
    @ppc.Attribute
    def _beta(self):
        """Side slope angle. [deg]"""
        if self.beta < 0 or self.beta > 90:
            warn("Invalid side slope angle", "Side slope angle must be between 0 and 90 degrees. Please enter a valid side slope angle.")
            raise ValueError("Side slope angle must be between 0 and 90 degrees.")
        return self.beta
    
    @ppc.Attribute
    def _phi_as(self):
        """Angle of repose of the armourstone. [deg]"""
        if self.phi_as < 0:
            warn("Invalid angle of repose", "Angle of repose must be positive. Please enter a valid angle of repose.")
            raise ValueError("Angle of repose must be positive.")
        return self.phi_as
    
    @ppc.Attribute
    def _psi_flow(self):
        """Angle made by the flow to the upslope direction. [deg]"""
        if self.psi_flow < 0:
            warn("Invalid flow angle", "Angle made by the flow to the upslope direction must be positive. Please enter a valid flow angle.")
            raise ValueError("Angle made by the flow to the upslope direction must be positive.")
        return self.psi_flow
    

class Ship(ppc.Base):
    inputs = ppc.Input(doc="Reference to the validated Inputs instance.")

    @ppc.Attribute
    def D_p(self):
        """Diameter of the propeller. [m]"""
        return self.inputs._D_p

    @ppc.Attribute
    def Z_p(self):
        """Propeller position, defined as the distance from the bed to the centre of the propeller. [m]"""
        return self.inputs._Z_p

    @ppc.Attribute
    def draught(self):
        """Distance from surface to lowest point of the hull. [m]"""
        return self.inputs._draught

    @ppc.Attribute
    def jet_velocity(self):
        """Target propeller jet velocity used in OpenFOAM. [m/s]"""
        return self.inputs._jet_velocity
    
    @ppc.Attribute
    def h(self):
        """Water depth. [m]"""
        return self.inputs._h
    
    @ppc.Attribute
    def d_slope(self):
        """Distance to slope. [m]"""
        return self.inputs._d_slope
    
    @ppc.Attribute
    def beta(self):
        """Side slope angle. [deg]"""
        return self.inputs._beta
    
    @ppc.Attribute
    def phi_as(self):
        """Angle of repose of the armourstone. [deg]"""
        return self.inputs._phi_as
    
    @ppc.Attribute
    def psi_flow(self):
        """Angle made by the flow to the upslope direction. [deg]"""
        return self.inputs._psi_flow


class Waterway(ppc.Base):
    inputs = ppc.Input(doc="Reference to the validated Inputs instance.")

    @ppc.Attribute
    def h(self):
        """Water depth. [m]"""
        return self.inputs._h
    


    @ppc.Attribute
    def beta_rad(self):
        """
        Convert the angle of the slope from degrees to radians.

        :return: Angle of the slope in radians. [rad]
        """
        return np.radians(self.beta)
    
    @ppc.Attribute
    def phi_as_rad(self):
        """
        Convert the angle of repose of the armourstone from degrees to radians.

        :return: Angle of repose of the armourstone in radians. [rad]
        """
        return np.radians(self.phi_as)
    
    @ppc.Attribute
    def psi_flow_rad(self):
        """
        Convert the angle made by the flow to the upslope direction from degrees to radians.

        :return: Angle made by the flow to the upslope direction in radians. [rad]
        """
        return np.radians(self.psi_flow)

    @ppc.Attribute
    def waterway_width(self):
        """
        Calculate the width of the waterway based on the distance to slope and the angle of the slope.

        :return: Width of the waterway. [m]
        """
        return self.h / np.tan(self.beta_rad)


class ArmourStone(ppc.Base):
    density_rock = ppc.Input(density_rock, doc="Density of the rock used for the armourstone. [kg/m^3]")
    density_water = ppc.Input(density_water, doc="Density of water. [kg/m^3]")
    psi_cr = ppc.Input(psi_cr, doc="Critical mobility parameter of the protection element. [-]")
    phi_sc = ppc.Input(phi_sc, doc="Stability correction factor. [-]")
    k_t2 = ppc.Input(k_t2, doc="Square of the turbulence factor. [-]")
    k_s = ppc.Input(k_s, doc="Roughness height of the armourstone. [m]")
    U = ppc.Input(manual_velocity, doc="Hydraulic loading velocity. This can be replaced by CFD. [m/s]")