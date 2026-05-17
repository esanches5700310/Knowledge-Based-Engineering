from parapy import core as ppc
from parapy.geom import Polygon

class Geometry(ppc.Base):

    waterway = ppc.Input()
    ship = ppc.Input()

    @ppc.Part
    def waterway_shape(self):
        return Polygon([
            (0, 0, -self.waterway.h),                                         # Leftmost point on bed
            (self.waterway.d_slope, 0, -self.waterway.h),                     # Begin of the slope
            (self.waterway.d_slope + self.waterway.waterway_width, 0, 0),     # End of the slope
            (0, 0, 0)                                                         # water surface left
        ], color="blue")

    @ppc.Part
    def propeller_shape(self):
        return Polygon([
            (-0.1, 0, -self.waterway.h + self.ship.Z_p + self.ship.D_p / 2),  # Top left point of propeller
            (-0.1, 0, -self.waterway.h + self.ship.Z_p - self.ship.D_p / 2),  # Bottom left point of propeller
            (0, 0, -self.waterway.h + self.ship.Z_p - self.ship.D_p / 2),     # Bottom right point of propeller
            (0, 0, -self.waterway.h + self.ship.Z_p + self.ship.D_p / 2)      # Top right point of propeller
        ], color="red")
    
    @ppc.Part
    def ship_shape(self):
        return Polygon([
            (-2, 0, 0),
            (-2, 0, -self.ship.draught),
            (-0.1, 0, -self.ship.draught),
            (-0.1, 0, 0)
        ], color="black")