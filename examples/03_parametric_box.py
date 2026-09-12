#!/usr/bin/env python3
"""
Example: Generate a parametric box
"""

from build123d import *

def create_parametric_box(width: float, height: float, depth: float, 
                         wall_thickness: float = 2.0) -> Part:
    """
    Create a parametric box with given dimensions.
    
    Args:
        width: Box width in mm
        height: Box height in mm
        depth: Box depth in mm
        wall_thickness: Wall thickness in mm
    
    Returns:
        Created Part object
    """
    with BuildPart() as bp:
        # Outer box
        Box(width, depth, height)
        
        # Inner cavity
        with BuildPart(mode=Mode.SUBTRACT):
            Box(
                width - 2*wall_thickness,
                depth - 2*wall_thickness,
                height - wall_thickness
            )
    
    return bp.part

if __name__ == "__main__":
    # Create box with custom dimensions
    box = create_parametric_box(width=100, height=50, depth=80, wall_thickness=3)
    box.save_stl("parametric_box.stl")
    print("Parametric box saved to parametric_box.stl")
