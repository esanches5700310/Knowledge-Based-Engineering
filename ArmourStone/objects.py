import numpy as np
from parapy import core as ppc
from input import *

class Ship(ppc.Base):
    D_p = ppc.Input(D_p, doc="Diameter of the propeller. [m]")
    Z_p = ppc.Input(Z_p, doc="Propeller position, defined as the distance from the bed to the centre of the propeller. [m]")
    draught = ppc.Input(draught, doc="Distance from surface to lowest point of the hull. [m]")
    jet_velocity = ppc.Input(jet_velocity, doc="Target propeller jet velocity used in OpenFOAM. [m/s]")


class Waterway(ppc.Base):
    h = ppc.Input(depth, doc="Water depth. [m]")
    d_slope = ppc.Input(propeller_to_slope_distance, doc="Distance to slope. [m]")
    beta = ppc.Input(beta, doc="Side slope angle. [deg]")
    phi_as = ppc.Input(phi_as, doc="Angle of repose of the armourstone. [deg]")
    psi_flow = ppc.Input(psi_flow, doc="Angle made by the flow to the upslope direction. [deg]")

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