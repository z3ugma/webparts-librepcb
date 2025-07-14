#!/usr/bin/env python3
"""
Test corner alignment with the refactored alignment system.
"""

import logging
from pathlib import Path

from adapters.easyeda.easyeda_api import EasyEDAApi
from adapters.easyeda.easyeda_footprint import EasyEDAFootprintParser
from adapters.librepcb.librepcb_footprint import (
    footprint_alignment_to_librepcb_settings,
)

logger = logging.getLogger(__name__)


def test_refactored_alignment():
    """Test the refactored, adapter-agnostic alignment system."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Initialize components
    api = EasyEDAApi()
    parser = EasyEDAFootprintParser()

    # Test with a specific component
    lcsc_id = "C2838500"

    print(f"\n=== Testing Refactored Alignment for {lcsc_id} ===\n")

    # Get component data
    cad_data = api.get_component_cad_data(lcsc_id)
    footprint = parser.parse_easyeda_json(cad_data)

    # Generate footprint files
    svg_data = api.get_and_cache_svg_data(lcsc_id)
    png_path, svg_path = api._generate_footprint_png_from_data(lcsc_id, svg_data)

    print(
        f"Footprint source offsets: X={footprint.source_offset_x}, Y={footprint.source_offset_y}"
    )

    # Calculate alignment using the parser's method
    alignment = parser.calculate_footprint_alignment(
        footprint=footprint, svg_path=svg_path, png_path=png_path
    )

    print("\nAlignment data:")
    print(f"  Scale factor: {alignment.svg_to_png_scale:.3f}")
    for ref in alignment.reference_points:
        print(
            f"    {ref.pad_number}: PNG({ref.source_x:.1f}, {ref.source_y:.1f}) -> MM({ref.target_x:.3f}, {ref.target_y:.3f})"
        )

    # Apply crosshairs to the test PNG (for visual verification)
    from svg_utils import overlay_alignment_crosshairs

    output_path = (
        Path(png_path).parent / f"test_alignment_with_crosshairs_{lcsc_id}.png"
    )
    overlay_alignment_crosshairs(png_path, alignment, str(output_path))
    print(f"\nSaved test image with crosshairs to: {output_path}")

    # Print LibrePCB settings
    print("\nLibrePCB settings:")
    print(footprint_alignment_to_librepcb_settings(alignment))


if __name__ == "__main__":
    test_refactored_alignment()
