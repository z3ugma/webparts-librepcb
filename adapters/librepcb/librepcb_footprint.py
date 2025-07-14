
from typing import List
from models.alignment import FootprintAlignment, AlignmentReference

def footprint_alignment_to_librepcb_settings(
    alignment: FootprintAlignment, enabled: bool
) -> str:
    """
    Generate the content for a LibrePCB `settings.lp` file from alignment data
    using a direct f-string approach, similar to librepcb-parts-generator.

    Args:
        alignment: The FootprintAlignment object containing reference points.
        enabled: A boolean to set the `enabled` flag in the settings file.

    Returns:
        A string containing the formatted S-expression.
    """
    enabled_str = "true" if enabled else "false"
    
    references_str = ""
    for ref in alignment.reference_points:
        references_str += (
            f"  (reference"
            f" (source {ref.source_x:.3f} {ref.source_y:.3f})"
            f" (target {ref.target_x:.3f} {ref.target_y:.3f}))\n"
        )

    return f"""(librepcb_background_image
 (enabled {enabled_str})
 (rotation 0.0)
{references_str})
"""
