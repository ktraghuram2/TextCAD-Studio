#!/usr/bin/env python3
"""
Example: Generate a simple cube
"""

from build123d import *

# Create a simple cube
with BuildPart() as bp:
    Box(10, 10, 10)  # 10mm cube

result = bp.part

# Export
if __name__ == "__main__":
    result.save_stl("cube.stl")
    print("Cube saved to cube.stl")
