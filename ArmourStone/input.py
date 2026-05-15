### Project parameters ###

project_name = "Armour Stone Design"
project_nr = "ASD-001"
output_path = "output/report.txt"

### Ship variables ###

D_p = 1.0             # Diameter of the propeller. [m]
Z_p = 5.0             # Propeller position, defined as the distance from the bed to the centre of the propeller. [m]
draught = 7         # Distance from surface to lowest point of the hull. [m]

### Waterway variables ###

depth = 10.0    # Depth of the waterway. [m]
d_slope = 20.0  # Horizontal distance to slope from propeller. [m]
beta = 30.0     # Side slope angle. [deg]
phi_as = 45.0   # Angle of repose of the armourstone. [deg]
psi_flow = 90   # Angle made by the flow to the upslope direction

### Pilarczyk parameters ###

density_rock = 2650  # Density of the rock used for the armourstone. [kg/m^3]
density_water = 1025 # Density of water. [kg/m^3]

phi_sc = 0.75   # Stability correction factor. [-] (0.75 for for continuous rock protection according to rock manual)
psi_cr = 0.035  # Critical mobility parameter of the protection element. [-] (0.035 for rip-rap and armourstone according to rock manual)
k_t2 = 4        # Square of the turbulence factor. [-] (k_t^2 > 3 according to rock manual)
k_s = 0.3       # Roughness height of the armourstone. [m] (k_s = 1 to 3*D_n50 according to rock manual)

### CFD variables ###

jet_velocity = 3.0          # Target propeller jet velocity used in OpenFOAM. [m/s]
upstream_length = 20.0      # Distance upstream of the propeller in the CFD domain. [m]
run_cfd = True             # If True, the app runs OpenFOAM automatically.
manual_velocity = 2.0       # Backup/design velocity used when run_cfd = False. [m/s]