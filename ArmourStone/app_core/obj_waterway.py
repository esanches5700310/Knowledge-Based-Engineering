import numpy as np
from parapy import core as ppc

class Waterway(ppc.Base):
    inputs = ppc.Input(doc="Reference to the validated Inputs instance.")

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