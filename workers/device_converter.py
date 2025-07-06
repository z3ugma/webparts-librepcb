import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from adapters.easyeda.easyeda_symbol import EasyEDASymbolParser
from adapters.easyeda.easyeda_footprint import EasyEDAParser
from adapters.librepcb.librepcb_device import LibrePCBDeviceSerializer
from adapters.librepcb.librepcb_uuid import create_derived_uuidv4
from constants import WebPartsFilename
from models.library_part import LibraryPart
from models.symbol import Symbol
from models.footprint import Footprint
from models.elements import LibrePCBElement
from workers.element_renderer import render_and_check_element

logger = logging.getLogger(__name__)


def process_device_complete(
    raw_cad_data: Dict[str, Any], library_part: LibraryPart
) -> Tuple[bool, Optional[Symbol], Optional[Footprint]]:
    """
    Complete device processing pipeline.

    This function orchestrates:
    1. Parsing the symbol and footprint data from EasyEDA.
    2. Generating the LibrePCB device file (.lp).
    3. Rendering the device and checking for issues.
    4. Updating the element's manifest (.wp) with validation results.
    """
    # Get the device directory from the library part
    dev_dir = library_part.device.dir_path
    if not dev_dir:
        logger.error("--- Device Generation Failed: No device directory path ---")
        return False, None, None

    # Step 1: Parse symbol and footprint data
    logger.info("--- Starting Device Generation ---")
    success, parsed_symbol, parsed_footprint = (
        _parse_symbol_and_footprint_from_cad_data(raw_cad_data)
    )

    if not success or not parsed_symbol or not parsed_footprint:
        error_msg = (
            "Device Generation Failed: Could not parse symbol or footprint data."
        )
        logger.error(f"--- {error_msg} ---")
        raise RuntimeError(error_msg)

    # Step 2: Generate the device file
    success = _generate_device_file(
        parsed_symbol, parsed_footprint, library_part, str(dev_dir)
    )

    if not success:
        logger.error("--- Device Generation Failed: Could not generate device file ---")
        return False, None, None

    logger.info("--- Device Generation Succeeded ---")

    # Step 3: Render, check, and update manifest
    _render_check_and_update_manifest(library_part, dev_dir)

    return True, parsed_symbol, parsed_footprint


def _parse_symbol_and_footprint_from_cad_data(
    raw_cad_data: Dict[str, Any],
) -> Tuple[bool, Optional[Symbol], Optional[Footprint]]:
    """Parse symbol and footprint data from raw CAD data."""
    if not raw_cad_data:
        logger.warning("No raw CAD data provided. Cannot parse symbol and footprint.")
        return False, None, None

    try:
        # Parse symbol data
        if not raw_cad_data.get("dataStr"):
            logger.warning("No dataStr found in raw CAD data. Cannot parse symbol.")
            return False, None, None

        logger.info("Parsing EasyEDA symbol data for device generation...")
        symbol_parser = EasyEDASymbolParser()
        canonical_symbol = symbol_parser.parse_easyeda_symbol(raw_cad_data)
        if not canonical_symbol:
            logger.error("Failed to parse symbol data from EasyEDA JSON.")
            return False, None, None
        logger.info(f"Successfully parsed symbol: {canonical_symbol.name}")

        # Parse footprint data
        if not raw_cad_data.get("packageDetail"):
            logger.warning(
                "No packageDetail found in raw CAD data. Cannot parse footprint."
            )
            return False, None, None

        logger.info("Parsing EasyEDA footprint data for device generation...")
        footprint_parser = EasyEDAParser()
        canonical_footprint = footprint_parser.parse_easyeda_json(
            raw_cad_data
        )  # Fixed method name
        if not canonical_footprint:
            logger.error("Failed to parse footprint data from EasyEDA JSON.")
            return False, None, None
        logger.info(f"Successfully parsed footprint: {canonical_footprint.name}")

        return True, canonical_symbol, canonical_footprint

    except Exception as e:
        logger.error(
            f"An error occurred during symbol/footprint parsing: {e}", exc_info=True
        )
        return False, None, None


def _generate_device_file(
    symbol: Symbol, footprint: Footprint, library_part: LibraryPart, dev_dir: str
) -> bool:
    """Generate the LibrePCB device file."""
    try:
        import uuid as uuid_module

        logger.info("Generating LibrePCB device file...")

        # Create device UUID from the library part UUID (device UUID is the main part UUID)
        main_uuid = uuid_module.UUID(library_part.uuid)
        device_uuid = main_uuid

        # Create component UUID from the library part UUID
        component_uuid = uuid_module.UUID(library_part.component.uuid)

        # Use the part name as the device name
        device_name = library_part.part_name

        # Serialize the device
        serializer = LibrePCBDeviceSerializer()
        serializer.serialize_to_file(
            symbol=symbol,
            footprint=footprint,
            dir_path=dev_dir,
            device_uuid=device_uuid,
            device_name=device_name,
            component_uuid=component_uuid,
            filename=LibrePCBElement.DEVICE.filename,
        )

        logger.info(
            f"Successfully generated device file: {dev_dir}/{LibrePCBElement.DEVICE.filename}"
        )
        return True

    except Exception as e:
        logger.error(
            f"An error occurred during device file generation: {e}", exc_info=True
        )
        return False


def _render_check_and_update_manifest(library_part: LibraryPart, dev_dir: Path):
    """Render the device, check for issues, and update the manifest."""
    try:
        logger.info("Rendering and checking device...")

        # Render and check the device
        _, issues = render_and_check_element(library_part, LibrePCBElement.DEVICE)

        # Update the manifest with validation results
        from library_manager import LibraryManager

        manager = LibraryManager()
        manager._update_element_manifest(
            LibrePCBElement.DEVICE, library_part.uuid, issues
        )

        logger.info("Device rendering and validation complete.")

    except Exception as e:
        logger.error(
            f"An error occurred during device rendering/checking: {e}", exc_info=True
        )
