### Project parameters ###

project_name = "Armour Stone Design"
project_nr = "ASD-001"
output_path = "output/report.txt"

### Ship variables ###

D_p = 1.0             # Diameter of the propeller. [m]
Z_p = 5.0             # Propeller position, defined as the distance from the bed to the centre of the propeller. [m]
keel_clearance = 0.5  # Distance from the bed to the lowest point of the hull. [m]
draught = 4.5         # Distance from surface to lowest point of the hull. [m]

### Waterway variables ###

depth = 10.0    # Depth of the waterway. [m]
d_slope = 20.0  # Distance to slope. [m]
slope = 30.0    # Angle of the slope. [deg]

### Pilarczyk parameters ###

density_rock = 2650  # Density of the rock used for the armourstone. [kg/m^3]
density_water = 1025 # Density of water. [kg/m^3]

phi_sc = 0.75   # Stability correction factor. [-] (0.75 for for continuous rock protection according to rock manual)
psi_cr = 0.035  # Critical mobility parameter of the protection element. [-] (0.035 for rip-rap and armourstone according to rock manual)
k_sl = 1.0      # Side slope factor. [-]
k_t = 1.6       # Turbulence factor. [-] (k_t^2 > 2 according to rock manual)