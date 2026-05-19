from parapy import core as ppc

class ArmourStone(ppc.Base):
    inputs = ppc.Input(doc="Reference to the validated Inputs instance.")

    @ppc.Attribute
    def density_rock(self):
        """Density of the rock used for the armourstone. [kg/m^3]"""
        return self.inputs._density_rock
    
    @ppc.Attribute
    def density_water(self):
        """Density of water. [kg/m^3]"""
        return self.inputs._density_water
    
    @ppc.Attribute
    def psi_cr(self):
        """Critical mobility parameter of the protection element. [-]"""
        return self.inputs._psi_cr
    
    @ppc.Attribute
    def phi_sc(self):
        """Stability correction factor. [-]"""
        return self.inputs._phi_sc
    
    @ppc.Attribute
    def k_t2(self):
        """Square of the turbulence factor. [-]"""
        return self.inputs._k_t2
    
    @ppc.Attribute
    def k_s(self):
        """Roughness height of the armourstone. [m]"""
        return self.inputs._k_s
    
    @ppc.Attribute
    def U(self):
        """Hydraulic loading velocity. This can be replaced by CFD. [m/s]"""
        return self.inputs._U