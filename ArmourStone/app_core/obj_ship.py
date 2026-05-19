from parapy import core as ppc

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