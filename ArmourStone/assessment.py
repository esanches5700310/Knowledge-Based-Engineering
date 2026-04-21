from parapy import core as ppc
from geometry import Ship, Waterway, ArmourStone

class ArmourStoneAssessment:
    inputPath = ppc.Input("input.py", doc="Path to the input file containing the parameters for the assessment. [str]")

    ship = Ship()
    waterway = Waterway()
    armourStone = ArmourStone()

    def report(self):
        # Generate and save the report.
        pass