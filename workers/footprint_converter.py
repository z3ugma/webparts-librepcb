import logging
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from librepcb_parts_generator.entities.package import Package

from adapters.easyeda.easyeda_footprint import EasyEDAFootprintParser
from constants import BACKGROUNDS_DIR, WebPartsFilename
from models.elements import LibrePCBElement
from models.library_part import LibraryPart
from workers.element_renderer import render_and_check_element

logger = logging.getLogger(__name__)


def process_footprint_complete(
    raw_cad_data: Dict[str, Any], library_part: LibraryPart, pkg_dir: Path
) -> Tuple[bool, Optional[Package]]:
    """
    Complete footprint processing pipeline.

    This function orchestrates:
    1. Generating the LibrePCB footprint file (.lp).
    2. Rendering the footprint to PNG and checking for issues.
    3. Updating the element's manifest (.wp) with validation results.
    4. Calculating alignment data and saving it to the LibrePCB backgrounds cache.
    5. Hydrating the part's name from the generated .lp file.
    """
    # Step 1: Generate the footprint
    logger.info("\n--- Starting Package Generation ---")
    success, parsed_package, offset_x, offset_y = _generate_footprint_file(
        raw_cad_data, str(pkg_dir)
    )

    if not success or not parsed_package:
        logger.error("--- Package Generation Failed ---")
        return False, None

    logger.info("--- Package Generation Succeeded ---")

    # Step 2: Render, check, and update manifest
    _render_check_and_update_manifest(library_part, pkg_dir)

    # Step 3: Calculate and save alignment data to backgrounds cache
    _calculate_and_save_alignment(parsed_package, pkg_dir, offset_x, offset_y)

    # Step 4: Hydrate metadata
    _hydrate_footprint_metadata(library_part, pkg_dir)

    return True, parsed_package


def _generate_footprint_file(
    raw_cad_data: Dict[str, Any], pkg_dir_str: str
) -> Tuple[bool, Optional[Package], float, float]:
    """
    Parses raw EasyEDA data and serializes it to a LibrePCB S-expression file.
    """
    if not raw_cad_data or not raw_cad_data.get("packageDetail"):
        logger.warning(
            "No packageDetail found in raw CAD data. Skipping footprint generation."
        )
        return False, None, 0.0, 0.0

    try:
        parser = EasyEDAFootprintParser()
        package, offset_x, offset_y = parser.parse_easyeda_json(raw_cad_data)
        if not package:
            logger.error("Failed to parse footprint data from EasyEDA JSON.")
            return False, None, 0.0, 0.0

        # LibrePCB-Parts-Generator's serializer appends the UUID, but we've already got it

        parent_dir = Path(*Path(pkg_dir_str).parts[0:-1])
        package.serialize(parent_dir)
        logger.info(f"Successfully serialized footprint to {pkg_dir_str}/package.lp")

        return True, package, offset_x, offset_y
    except Exception as e:
        logger.error(
            f"An error occurred during footprint generation: {e}", exc_info=True
        )
        return False, None, 0.0, 0.0


def _render_check_and_update_manifest(library_part: LibraryPart, pkg_dir: Path):
    """
    Render the footprint, run checks, and update the .wp manifest file.
    """
    try:
        # Note: render_and_check_element uses the LibraryPart object, which is why it's passed down.
        # It needs the UUIDs to construct paths internally.
        _, issues = render_and_check_element(library_part, LibrePCBElement.PACKAGE)
        logger.info("Package rendering and checking completed.")

        from library_manager import LibraryManager

        manager = LibraryManager()
        manager._update_element_manifest(
            LibrePCBElement.PACKAGE, library_part.footprint.uuid, issues
        )
        logger.info(f"Updated footprint manifest with {len(issues)} validation issues.")
    except Exception as e:
        logger.error(f"Failed to render, check, or update manifest: {e}", exc_info=True)


def _calculate_and_save_alignment(
    package: Package, pkg_dir: Path, offset_x: float, offset_y: float
) -> None:
    """
    Calculate alignment and save settings/image to the backgrounds directory.
    """
    from adapters.librepcb.librepcb_footprint import (
        footprint_alignment_to_librepcb_settings,
    )
    from models.alignment import AlignmentCalculator
    from svg_utils import (
        create_coordinate_mapper,
        get_png_dimensions,
        overlay_alignment_crosshairs,
        parse_svg_viewbox,
    )
    from librepcb_parts_generator.entities.common import Name

    svg_path = pkg_dir / WebPartsFilename.FOOTPRINT_SVG.value
    png_path = pkg_dir / WebPartsFilename.FOOTPRINT_PNG.value

    if not svg_path.exists() or not png_path.exists():
        logger.warning(f"Missing SVG or PNG for alignment in {pkg_dir}, skipping.")
        return

    # Find the top package outline polygon from the default footprint
    footprint = next((fp for fp in package.footprints if fp.name.value == "default"), None)
    if not footprint:
        logger.warning("Default footprint not found in package, skipping alignment.")
        return

    outline_polygon = None
    for polygon in footprint.polygons:
        if polygon.layer.layer == "top_package_outlines":
            outline_polygon = polygon
            break

    if not outline_polygon:
        logger.warning("No 'top_package_outlines' polygon found, skipping alignment.")
        return

    # Set up the coordinate mapper
    viewbox = parse_svg_viewbox(str(svg_path))
    png_dims = get_png_dimensions(str(png_path))
    UNIT_SCALE = 0.254  # Must match the parser's scale

    coordinate_mapper = create_coordinate_mapper(
        svg_info=viewbox,
        png_info=png_dims,
        source_offset_x=offset_x / UNIT_SCALE,  # Convert offset back to source units
        source_offset_y=offset_y / UNIT_SCALE,
        unit_scale=UNIT_SCALE,
    )

    # Calculate alignment using the new polygon-based calculator
    calculator = AlignmentCalculator()
    alignment = calculator.calculate_alignment_from_polygon(
        polygon=outline_polygon, coordinate_mapper=coordinate_mapper
    )

    if alignment:
        # Overlay crosshairs and save files
        overlay_alignment_crosshairs(str(png_path), alignment)
        alignment_settings = footprint_alignment_to_librepcb_settings(
            alignment, enabled=True
        )
        _copy_to_backgrounds_directory(package.uuid, str(png_path), alignment_settings)
    else:
        logger.warning(
            "Could not calculate alignment data, skipping background image generation."
        )


def _hydrate_footprint_metadata(library_part: LibraryPart, pkg_dir: Path) -> None:
    """
    Hydrate footprint metadata like the name from the package.lp file.
    """
    footprint_name = LibrePCBElement.PACKAGE.get_element_name(
        library_part.footprint.uuid
    )
    if footprint_name:
        library_part.footprint.name = footprint_name
        logger.info(f"Hydrated footprint name: {footprint_name}")


def _copy_to_backgrounds_directory(
    footprint_uuid: str, png_with_crosshairs_path: str, alignment_settings: str
) -> None:
    """
    Copy footprint PNG and alignment settings to LibrePCB backgrounds directory.
    """
    try:
        # Convert UUID to string for path joining
        background_dir = BACKGROUNDS_DIR / str(footprint_uuid)
        background_dir.mkdir(parents=True, exist_ok=True)

        # Copy PNG as image.png
        shutil.copy2(png_with_crosshairs_path, background_dir / "image.png")

        # Write settings.lp
        (background_dir / "settings.lp").write_text(alignment_settings)

        logger.info(
            f"Copied alignment files to backgrounds directory: {background_dir}"
        )
    except Exception as e:
        logger.error(f"Failed to copy to backgrounds directory: {e}", exc_info=True)
