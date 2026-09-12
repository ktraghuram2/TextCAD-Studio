#!/usr/bin/env python3
"""
Example: Generate a cylindrical container with hexagonal holes
"""

from build123d import *
import math

# Create cylindrical container
with BuildPart() as bp:
    # Outer cylinder
    Cylinder(radius=25, height=100)
    
    # Inner cavity (subtract)
    with BuildPart(mode=Mode.SUBTRACT):
        Cylinder(radius=23, height=98)
    
    # Hexagonal hole pattern on bottom
    hole_radius = 5
    pattern_radius = 15
    
    for i in range(6):
        angle = i * math.pi / 3
        x = pattern_radius * math.cos(angle)
        y = pattern_radius * math.sin(angle)
        
        with Locations((x, y, 0)):
            with BuildPart(mode=Mode.SUBTRACT):
                Cylinder(radius=hole_radius, height=5)

result = bp.part

if __name__ == "__main__":
    result.save_stl("container.stl")
    print("Container saved to container.stl")
