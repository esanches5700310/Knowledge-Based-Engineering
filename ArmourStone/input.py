### Project parameters ###

project_name = "Armour Stone Design"
project_nr = "ASD-001"
output_path = "output/report.txt"

### Ship variables ###

D_p = 1.0             # Diameter of the propeller. [m]
Z_p = 5.0             # Propeller position, defined as the distance from the bed to the centre of the propeller. [m]
draught = 7           # Distance from surface to lowest point of the hull. [m]

### Waterway variables ###

depth = 10.0                        # Depth of the waterway. [m]
propeller_to_slope_distance = 5.0  # Horizontal distance to slope from propeller. [m]
beta = 30.0                         # Side slope angle. [deg]
phi_as = 45.0                       # Angle of repose of the armourstone. [deg]
psi_flow = 90                       # Angle made by the flow to the upslope direction

### Pilarczyk parameters ###

density_rock = 2650  # Density of the rock used for the armourstone. [kg/m^3]
density_water = 1025 # Density of water. [kg/m^3]

phi_sc = 0.75   # Stability correction factor. [-] (0.75 for for continuous rock protection according to rock manual)
psi_cr = 0.035  # Critical mobility parameter of the protection element. [-] (0.035 for rip-rap and armourstone according to rock manual)
k_t2 = 4        # Square of the turbulence factor. [-] (k_t^2 > 3 according to rock manual)
k_s = 0.3       # Roughness height of the armourstone. [m] (k_s = 1 to 3*D_n50 according to rock manual)

### CFD variables ###

run_cfd = True              # If True, the app runs OpenFOAM automatically.
manual_velocity = 2.0       # Backup/design velocity used when run_cfd = False. [m/s]

jet_velocity = 3.0          # Target propeller jet velocity used in OpenFOAM. [m/s]

### CFD simulation selection ###

openfoam_simulation_type = "2D"   # Choose "2D" or "3D"

# Distance from left boundary to propeller centre
# This is larger in 2D because the return flow is constrained in the x-z plane.
cfd_left_boundary_to_propeller_2d = 20.0  # [m]

# This can be smaller in 3D because the flow can spread laterally.
cfd_left_boundary_to_propeller_3d = 1.0   # [m]

# 3D CFD settings
cfd_domain_width_3d = 12.0        # Width of the 3D CFD domain. [m]

# Mesh settings: 2D
cfd_cells_flat_x_2d = 240
cfd_cells_slope_x_2d = 80
cfd_cells_z_2d = 80

# Mesh settings: 3D
cfd_cells_flat_x_3d = 180
cfd_cells_slope_x_3d = 60
cfd_cells_y_3d = 36
cfd_cells_z_3d = 50