import numpy as np
from parapy import core as ppc
from input import *
from parapy.geom import Polygon

class Ship(ppc.Base):
    D_p = ppc.Input(D_p, doc="Diameter of the propeller. [m]")
    Z_p = ppc.Input(Z_p, doc="Propeller position, defined as the distance from the bed to the centre of the propeller. [m]")
    keel_clearance = ppc.Input(keel_clearance, doc="Distance from the bed to the lowest point of the hull. [m] ")
    draught = ppc.Input(draught, doc="Distance from surface to lowest point of the hull. [m]")


class Waterway(ppc.Base):
    h = ppc.Input(depth, doc="Water depth. [m]")
    d_slope = ppc.Input(d_slope, doc="Distance to slope. [m]")
    alpha = ppc.Input(alpha, doc="Angle of the slope. [deg]")
    phi_as = ppc.Input(phi_as, doc="Angle of repose of the armourstone. [deg]")
    beta = ppc.Input(beta, doc="Longitudinal slope angle. [deg]")

    @ppc.Attribute
    def waterway_width(self):
        """
        Calculate the width of the waterway based on the distance to slope and the angle of the slope.

        :return: Width of the waterway. [m]
        """
        return self.d_slope * np.tan(np.radians(self.alpha))


class ArmourStone(ppc.Base):
    density_rock = ppc.Input(density_rock, doc="Density of the rock used for the armourstone. [kg/m^3]")
    density_water = ppc.Input(density_water, doc="Density of water. [kg/m^3]")
    psi_cr = ppc.Input(psi_cr, doc="Critical mobility parameter of the protection element. [-]")
    phi_sc = ppc.Input(phi_sc, doc="Stability correction factor. [-]")
    k_t2 = ppc.Input(k_t2, doc="Square of the turbulence factor. [-]")
    k_s = ppc.Attribute(k_s, doc="Roughness height of the armourstone. [m]")
    U = 1 # NEED TO GET THIS OUT OF CFD SIMULATION