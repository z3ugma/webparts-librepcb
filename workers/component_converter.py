import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from adapters.easyeda.easyeda_symbol import EasyEDASymbolParser
from adapters.librepcb.librepcb_component import LibrePCBComponentSerializer
from adapters.librepcb.librepcb_uuid import create_derived_uuidv4
from constants import WebPartsFilename
from models.library_part import LibraryPart
from models.symbol import Symbol
from models.elements import LibrePCBElement
from workers.element_renderer import render_and_check_element

logger = logging.getLogger(__name__)


def process_component_complete(
    raw_cad_data: Dict[str, Any], library_part: LibraryPart
) -> Tuple[bool, Optional[Symbol]]:
    """
    Complete component processing pipeline.

    This function orchestrates:
    1. Parsing the symbol data from EasyEDA.
    2. Generating the LibrePCB component file (.lp).
    3. Rendering the component and checking for issues.
    4. Updating the element's manifest (.wp) with validation results.
    5. Hydrating the part's name from the generated .lp file.
    """
    # Get the component directory from the library part
    cmp_dir = library_part.component.dir_path
    if not cmp_dir:
        logger.error("--- Component Generation Failed: No component directory path ---")
        return False, None

    # Step 1: Parse symbol data
    logger.info("--- Starting Component Generation ---")
    success, parsed_symbol = _parse_symbol_from_cad_data(raw_cad_data)

    if not success or not parsed_symbol:
        logger.error("--- Component Generation Failed: Could not parse symbol data ---")
        return False, None

    # Step 2: Generate the component file
    success = _generate_component_file(parsed_symbol, library_part, str(cmp_dir))

    if not success:
        logger.error(
            "--- Component Generation Failed: Could not generate component file ---"
        )
        return False, None

    logger.info("--- Component Generation Succeeded ---")

    # Step 3: Render, check, and update manifest
    _render_check_and_update_manifest(library_part, cmp_dir)

    return True, parsed_symbol


def _parse_symbol_from_cad_data(
    raw_cad_data: Dict[str, Any],
) -> Tuple[bool, Optional[Symbol]]:
    """Parse symbol data from raw CAD data."""
    if not raw_cad_data or not raw_cad_data.get("dataStr"):
        logger.warning("No dataStr found in raw CAD data. Cannot parse symbol.")
        return False, None

    try:
        logger.info("Parsing EasyEDA symbol data for component generation...")
        symbol_parser = EasyEDASymbolParser()
        canonical_symbol = symbol_parser.parse_easyeda_symbol(raw_cad_data)
        if not canonical_symbol:
            logger.error("Failed to parse symbol data from EasyEDA JSON.")
            return False, None
        logger.info(f"Successfully parsed symbol: {canonical_symbol.name}")
        return True, canonical_symbol

    except Exception as e:
        logger.error(f"An error occurred during symbol parsing: {e}", exc_info=True)
        return False, None


def _generate_component_file(
    symbol: Symbol, library_part: LibraryPart, cmp_dir: str
) -> bool:
    """Generate the LibrePCB component file."""
    try:
        import uuid as uuid_module

        logger.info("Generating LibrePCB component file...")

        # Create component UUID from the library part UUID
        main_uuid = uuid_module.UUID(library_part.uuid)
        component_uuid = create_derived_uuidv4(main_uuid, "component")

        # Use the part name as the component name
        component_name = library_part.part_name

        # Serialize the component
        serializer = LibrePCBComponentSerializer()
        serializer.serialize_to_file(
            symbol=symbol,
            dir_path=cmp_dir,
            component_uuid=component_uuid,
            component_name=component_name,
            filename=LibrePCBElement.COMPONENT.filename,
        )

        logger.info(
            f"Successfully generated component file: {cmp_dir}/{LibrePCBElement.COMPONENT.filename}"
        )
        return True

    except Exception as e:
        logger.error(
            f"An error occurred during component file generation: {e}", exc_info=True
        )
        return False


def _render_check_and_update_manifest(library_part: LibraryPart, cmp_dir: Path):
    """Render the component, check for issues, and update the manifest."""
    try:
        logger.info("Rendering and checking component...")

        # Render and check the component
        _, issues = render_and_check_element(library_part, LibrePCBElement.COMPONENT)

        # Update the manifest with validation results
        from library_manager import LibraryManager

        manager = LibraryManager()
        manager._update_element_manifest(
            LibrePCBElement.COMPONENT, library_part.component.uuid, issues
        )

        logger.info("Component rendering and validation complete.")

    except Exception as e:
        logger.error(
            f"An error occurred during component rendering/checking: {e}", exc_info=True
        )
