import logging
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from adapters.easyeda.easyeda_footprint import EasyEDAParser
from adapters.librepcb.librepcb_footprint import (
    LibrePCBFootprintSerializer,
    footprint_alignment_to_librepcb_settings,
)
from constants import BACKGROUNDS_DIR, WebPartsFilename
from models.footprint import Footprint
from models.library_part import LibraryPart
from workers.element_renderer import render_and_check_element
from models.elements import LibrePCBElement


logger = logging.getLogger(__name__)


def process_footprint_complete(
    raw_cad_data: Dict[str, Any], library_part: LibraryPart, pkg_dir: Path
) -> Tuple[bool, Optional[Footprint]]:
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
    logger.info("--- Starting Footprint Generation ---")
    success, parsed_footprint = _generate_footprint_file(raw_cad_data, str(pkg_dir))

    if not success or not parsed_footprint:
        logger.error("--- Footprint Generation Failed ---")
        return False, None

    logger.info("--- Footprint Generation Succeeded ---")

    # Step 2: Render, check, and update manifest
    _render_check_and_update_manifest(library_part, pkg_dir)

    # Step 3: Calculate and save alignment data to backgrounds cache
    _calculate_and_save_alignment(parsed_footprint, pkg_dir)

    # Step 4: Hydrate metadata
    _hydrate_footprint_metadata(library_part, pkg_dir)

    return True, parsed_footprint


def _generate_footprint_file(
    raw_cad_data: Dict[str, Any], pkg_dir_str: str
) -> Tuple[bool, Optional[Footprint]]:
    """
    Parses raw EasyEDA data and serializes it to a LibrePCB S-expression file.
    """
    if not raw_cad_data or not raw_cad_data.get("packageDetail"):
        logger.warning(
            "No packageDetail found in raw CAD data. Skipping footprint generation."
        )
        return False, None

    try:
        parser = EasyEDAParser()
        footprint = parser.parse_easyeda_json(raw_cad_data)
        if not footprint:
            logger.error("Failed to parse footprint data from EasyEDA JSON.")
            return False, None

        serializer = LibrePCBFootprintSerializer(invert_y=True)
        serializer.serialize_to_file(footprint, pkg_dir_str)
        logger.info(f"Successfully serialized footprint to {pkg_dir_str}/package.lp")

        return True, footprint
    except Exception as e:
        logger.error(
            f"An error occurred during footprint generation: {e}", exc_info=True
        )
        return False, None


def _render_check_and_update_manifest(library_part: LibraryPart, pkg_dir: Path):
    """
    Render the footprint, run checks, and update the .wp manifest file.
    """
    try:
        # Note: render_and_check_element uses the LibraryPart object, which is why it's passed down.
        # It needs the UUIDs to construct paths internally.
        _, issues = render_and_check_element(library_part, LibrePCBElement.PACKAGE)
        logger.info("Footprint rendering and checking completed.")

        from library_manager import LibraryManager

        manager = LibraryManager()
        manager._update_element_manifest(
            LibrePCBElement.PACKAGE, library_part.footprint.uuid, issues
        )
        logger.info(f"Updated footprint manifest with {len(issues)} validation issues.")
    except Exception as e:
        logger.error(f"Failed to render, check, or update manifest: {e}", exc_info=True)


def _calculate_and_save_alignment(footprint: Footprint, pkg_dir: Path) -> None:
    """
    Calculate alignment and save settings/image to the backgrounds directory.
    """
    svg_path = pkg_dir / WebPartsFilename.FOOTPRINT_SVG.value
    png_path = pkg_dir / WebPartsFilename.FOOTPRINT_PNG.value

    if not svg_path.exists() or not png_path.exists():
        logger.warning(
            f"Missing SVG or PNG files in {pkg_dir} for alignment, skipping."
        )
        return

    parser = EasyEDAParser()
    alignment = parser.calculate_footprint_alignment(
        footprint=footprint, svg_path=str(svg_path), png_path=str(png_path)
    )

    if alignment:
        from svg_utils import overlay_alignment_crosshairs
        from adapters.librepcb.librepcb_footprint import (
            footprint_alignment_to_librepcb_settings,
        )

        # Overlay crosshairs directly onto the final PNG
        overlay_alignment_crosshairs(str(png_path), alignment)

        # Create alignment settings content
        alignment_settings = footprint_alignment_to_librepcb_settings(
            alignment, enabled=True
        )

        # Save both to the LibrePCB backgrounds directory
        _copy_to_backgrounds_directory(
            footprint.uuid, str(png_path), alignment_settings
        )
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
