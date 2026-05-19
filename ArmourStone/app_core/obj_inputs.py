from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))

from input import *
from parapy import core as ppc
from app_core.warning import warn

class Inputs(ppc.Base):
    """
    Class to do input handling and validation. Passes the validated inputs through to the other classes.
    """
    # Ship variables
    D_p = ppc.Input(D_p, doc="Diameter of the propeller. [m]")
    Z_p = ppc.Input(Z_p, doc="Propeller position, defined as the distance from the bed to the centre of the propeller. [m]")
    draught = ppc.Input(draught, doc="Distance from surface to lowest point of the hull. [m]")
    jet_velocity = ppc.Input(jet_velocity, doc="Target propeller jet velocity used in OpenFOAM. [m/s]")

    # Waterway variables
    h = ppc.Input(depth, doc="Water depth. [m]")
    d_slope = ppc.Input(propeller_to_slope_distance, doc="Distance to slope. [m]")
    beta = ppc.Input(beta, doc="Side slope angle. [deg]")
    phi_as = ppc.Input(phi_as, doc="Angle of repose of the armourstone. [deg]")
    psi_flow = ppc.Input(psi_flow, doc="Angle made by the flow to the upslope direction. [deg]")

    # Pilarczyk parameters
    density_rock = ppc.Input(density_rock, doc="Density of the rock used for the armourstone. [kg/m^3]")
    density_water = ppc.Input(density_water, doc="Density of water. [kg/m^3]")
    psi_cr = ppc.Input(psi_cr, doc="Critical mobility parameter of the protection element. [-]")
    phi_sc = ppc.Input(phi_sc, doc="Stability correction factor. [-]")
    k_t2 = ppc.Input(k_t2, doc="Square of the turbulence factor. [-]")
    k_s = ppc.Input(k_s, doc="Roughness height of the armourstone. [m]")
    U = ppc.Input(manual_velocity, doc="Hydraulic loading velocity. This can be replaced by CFD. [m/s]")

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
    
    @ppc.Attribute
    def _density_rock(self):
        """Density of the rock used for the armourstone. [kg/m^3]"""
        if self.density_rock <= 0:
            warn("Invalid rock density", "Density of the rock must be a positive value. Please enter a valid rock density.")
            raise ValueError("Density of the rock must be positive.")
        return self.density_rock
    
    @ppc.Attribute
    def _density_water(self):
        """Density of water. [kg/m^3]"""
        if self.density_water <= 0:
            warn("Invalid water density", "Density of water must be a positive value. Please enter a valid water density.")
            raise ValueError("Density of water must be positive.")
        return self.density_water
    
    @ppc.Attribute
    def _psi_cr(self):
        """Critical mobility parameter of the protection element. [-]"""
        if self.psi_cr < 0:
            warn("Invalid critical mobility parameter", "Critical mobility parameter must be a positive value. Please enter a valid critical mobility parameter.")
            raise ValueError("Critical mobility parameter must be positive.")
        return self.psi_cr
    
    @ppc.Attribute
    def _phi_sc(self):
        """Stability correction factor. [-]"""
        if self.phi_sc < 0:
            warn("Invalid stability correction factor", "Stability correction factor must be a positive value. Please enter a valid stability correction factor.")
            raise ValueError("Stability correction factor must be positive.")
        return self.phi_sc
    
    @ppc.Attribute
    def _k_t2(self):
        """Square of the turbulence factor. [-]"""
        if self.k_t2 < 0:
            warn("Invalid turbulence factor", "Square of the turbulence factor must be a positive value. Please enter a valid turbulence factor.")
            raise ValueError("Square of the turbulence factor must be positive.")
        return self.k_t2
    
    @ppc.Attribute
    def _k_s(self):
        """Roughness height of the armourstone. [m]"""
        if self.k_s < 0:
            warn("Invalid roughness height", "Roughness height of the armourstone must be a positive value. Please enter a valid roughness height.")
            raise ValueError("Roughness height of the armourstone must be positive.")
        return self.k_s
    
    @ppc.Attribute
    def _U(self):
        """Hydraulic loading velocity. This can be replaced by CFD. [m/s]"""
        if self.U < 0:
            warn("Invalid hydraulic loading velocity", "Hydraulic loading velocity must be a positive value. Please enter a valid hydraulic loading velocity.")
            raise ValueError("Hydraulic loading velocity must be positive.")
        return self.U