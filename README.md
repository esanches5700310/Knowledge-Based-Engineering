# Knowledge-Based-Engineering

This code is part of the AE4204 Knowledge Based Engineering course at Delft University of Technology

**Authors:**

Estevam Sanches & Robbe Truyts

This is done as part of the company assignment from Fugro, unauthorized use is forbidden.


# ArmourStone KBE Application

This app assesses underwater armour stone loading from a propeller jet.
It uses ParaPy, simplified OpenFOAM CFD, and analytical design rules.

## Main files
- `main.py`: starts the app and opens the ParaPy GUI.
- `input.py`: contains the default project inputs.
- `app_core/`: contains the main app logic.

## Requirements
- Python
- ParaPy
- Docker Desktop
- OpenFOAM through Docker
- ParaView, optional for CFD visualization

Docker Desktop must be open before running CFD.

## How to run
1. Open Docker Desktop.
2. Open the project in your Python IDE.
3. Run `python main.py`.
4. The ParaPy GUI should open automatically.

## Changing inputs
Inputs can be changed in `input.py` or directly in the ParaPy GUI.
Typical editable inputs are propeller diameter, propeller position,
water depth, slope angle, material properties, CFD settings, and 2D/3D mode.
After changing GUI inputs, refresh or evaluate the model.

## CFD settings
To run OpenFOAM automatically:
```python
run_cfd = True
```
To skip CFD and use a manual velocity:
```python
run_cfd = False
manual_velocity = 2.0
```
Choose the CFD type with:
```python
openfoam_simulation_type = "2D"  # or "3D"
```

## Notes
- Keep Docker open when `run_cfd = True`.
- 3D CFD is slower than 2D CFD (2D takes about 3min in a good computer while 3D can take around 1h)
- Mesh settings can be edited in `input.py`.
- The CFD model is simplified for engineering decision support.
- ParaView can be used to inspect OpenFOAM results.

## Troubleshooting
If CFD fails, check Docker and OpenFOAM.
If the GUI fails, check ParaPy and the Python environment.
To test without CFD, set `run_cfd = False`.

## Output
The app calculates hydraulic loading and required armour stone size.
Results can be inspected in the GUI and exported with the app tools.
