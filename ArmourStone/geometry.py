import numpy as np
from parapy import core as ppc
from input import *

class Ship:
    D_p = ppc.Input(D_p, doc="Diameter of the propeller. [m]")
    Z_p = ppc.Input(Z_p, doc="Propeller position, defined as the distance from the bed to the centre of the propeller. [m]")
    keel_clearance = ppc.Input(keel_clearance, doc="Distance from the bed to the lowest point of the hull. [m] ")
    draught = ppc.Input(draught, doc="Distance from surface to lowest point of the hull. [m]")


class Waterway:
    depth = ppc.Input(depth, doc="Water depth. [m]")
    d_slope = ppc.Input(d_slope, doc="Distance to slope. [m]")
    slope = ppc.Input(slope, doc="Angle of the slope. [deg]")


class ArmourStone:
    density_rock = ppc.Input(density_rock, doc="Density of the rock used for the armourstone. [kg/m^3]")
    density_water = ppc.Input(density_water, doc="Density of water. [kg/m^3]")
    psi_cr = ppc.Input(psi_cr, doc="Critical mobility parameter of the protection element. [-]")
    phi_sc = ppc.Input(phi_sc, doc="Stability correction factor. [-]")
    h = ppc.Input(depth, doc="Water depth. [m]")
    k_sl = ppc.Input(k_sl, doc="Side slope factor. [-]")
    k_t = ppc.Input(k_t, doc="Turbulence factor. [-]")
    U = None # NEED TO GET THIS OUT OF CFD SIMULATION


    @ppc.Attribute
    def delta(self):
        """
        Calculate the relative buoyant density of the protection element.

        :return: Relative buoyant density of the protection element. [-]
        """
        return self.density_rock / self.density_water - 1
    
    @ppc.Attribute
    def k_h(self):
        """
        Calculate the velocity profile factor.

        :return: Velocity profile factor. [-]
        """
        return 2 / (np.log(1 + 12 * self.h / self.k_s)**2)

    def pilarczyk(self):
        """
        Calculate the required stone diameter according to Pilarczyk (1995).

        :param phi_sc: Stability correction factor. [-]
        :param delta: Relative buoyant density of the protection element. [-]
        :param psi_cr: Critical mobility parameter of the protection element. [-]
        :param k_h: Velocity profile factor. [-]
        :param k_sl: Side slope factor. [-]
        :param k_t: Turbulence factor. [-]
        :param U: Depth-averaged flow velocity. [m/s]
        :return: Characteristic size of the protection element [m]. D = D_n50 for armourstone.
        """
        g = 9.80665  # Acceleration due to gravity [m/s^2]

        # Calculate the required stone diameter using Pilarczyk's formula
        D = self.phi_sc / self.delta * 0.035 / self.psi_cr * self.k_h * self.k_sl**(-1) * self.k_t**2 * self.U**2 / (2 *g)

        return D