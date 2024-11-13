import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Parameters
r = 5            # Radius of the outer circle
n_outer = 18     # Number of points on the outer circle
n_inner = 18     # Initial number of points on the inner circle

# Step 1: Create the outer circle and the red points on it
theta_outer = np.linspace(0, 2 * np.pi, n_outer, endpoint=False)
outer_points_x = r * np.cos(theta_outer)
outer_points_y = r * np.sin(theta_outer)

# Step 2: Calculate distance between two adjacent points on the outer circle
d = np.sqrt((outer_points_x[1] - outer_points_x[0])**2 + (outer_points_y[1] - outer_points_y[0])**2)

# Step 3: Define radius for the inner circle
s = r - d

# Step 4: Create 18 points on the inner circle, offset by half the angle between points to position them correctly
angle_offset = np.pi / n_outer  # Half the radial distance
theta_inner = np.linspace(0, 2 * np.pi, n_inner, endpoint=False) + angle_offset
inner_points_x = s * np.cos(theta_inner)
inner_points_y = s * np.sin(theta_inner)

# Separate inner points into alternating points for red dots and for square positions
inner_points_x_dots = inner_points_x[::2]
inner_points_y_dots = inner_points_y[::2]
square_angles = theta_inner[1::2]  # Angles for the squares

# Step 5: Calculate the side length of each square so it spans from inner circle to outer circle
square_side = d * 0.8  # Side length that matches the gap between points on the inner circle

# Plot setup
fig, ax = plt.subplots()
ax.set_aspect('equal')
ax.set_xlim(-r - 1, r + 1)
ax.set_ylim(-r - 1, r + 1)

# Remove tick marks and axis numbers
ax.set_xticks([])
ax.set_yticks([])
ax.axis('off')

# Draw the outer circle and outer points
outer_circle = plt.Circle((0, 0), r, fill=False, linestyle='--', edgecolor='blue')
ax.add_patch(outer_circle)
ax.scatter(outer_points_x, outer_points_y, color='red', s=50, label='Extractors')

# Draw the inner circle and alternating red points
inner_circle = plt.Circle((0, 0), s, fill=False, linestyle='--', edgecolor='green')
ax.add_patch(inner_circle)
ax.scatter(inner_points_x_dots, inner_points_y_dots, color='red', s=50)

# Draw squares with their centers pushed outward by half the side length
not_draw_counter = 0
for angle in square_angles:
    not_draw_counter += 1
    if not_draw_counter > 3 and not_draw_counter < 7:
        continue
    # Calculate the initial center of each square at the missing point position on the inner circle
    initial_square_center_x = s * np.cos(angle)
    initial_square_center_y = s * np.sin(angle)

    # Push the square center outward by half the square's side length
    square_center_x = initial_square_center_x + (square_side / 2) * np.cos(angle)
    square_center_y = initial_square_center_y + (square_side / 2) * np.sin(angle)

    # Create a square patch centered at the adjusted position with correct rotation
    square = patches.RegularPolygon(
        (square_center_x, square_center_y),  # Center of the square
        numVertices=4,                      # Number of vertices for a square
        radius=square_side / np.sqrt(2),    # Set radius so the square's side matches the desired length
        orientation=angle - np.pi / 4,      # Rotate 45 degrees to face the center
        edgecolor='purple', linewidth=1.5, fill=False
    )
    ax.add_patch(square)

# Display the plot with legend
plt.legend()
plt.show()
