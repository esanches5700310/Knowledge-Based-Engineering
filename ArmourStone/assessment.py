import numpy as np
from parapy import core as ppc
from parapy.gui import display
from geometry import Ship, Waterway, ArmourStone

class ArmourStoneAssessment(ppc.Base):
    inputPath = ppc.Input("input.py", doc="Path to the input file containing the parameters for the assessment. [str]")

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
    def k_d(self):
        """
        Calculate the side slope term.
        
        :return: Side slope term. [-]
        """
        return (1 - (np.sin(self.waterway.alpha)**2 / np.sin(self.waterway.phi_as)**2))**(0.5)
    
    @ppc.Attribute
    def k_l(self):
        """
        Calculate the longitudinal slope term.

        :return: Longitudinal slope term. [-]
        """
        return np.sin(self.waterway.phi_as - self.waterway.beta) / np.sin(self.waterway.phi_as)

    @ppc.Attribute
    def k_sl(self):
        """
        Calculate the side slope factor.

        :return: Side slope factor. [-]
        """
        return self.k_d * self.k_l

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
        D = self.armourStone.phi_sc / self.delta * 0.035 / self.armourStone.psi_cr * self.k_h * self.k_sl**(-1) * self.armourStone.k_t2**2 * self.armourStone.U**2 / (2 * g)

        return D

    def report(self):
        """
        Generate and save the report.
        """
        pass

    def run(self):
        """
        Run the assessment.
        """
        self.generateGeometry()
        D_required = self.pilarczyk()
        print(f"Required stone diameter according to Pilarczyk's formula: {D_required:.2f} m")

test = ArmourStoneAssessment()
test.run()