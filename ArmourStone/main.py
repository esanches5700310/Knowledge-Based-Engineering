from parapy.gui import display
from app_core.assessment import ArmourStoneAssessment


if __name__ == "__main__":
    app = ArmourStoneAssessment()
    app.evaluate_all(max_depth=1)
    display(app, view="front", autodraw=True)