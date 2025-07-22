from collections import defaultdict
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from librepcb_parts_generator.entities.symbol import Symbol, Pin

from adapters.easyeda.easyeda_symbol import EasyEDASymbolParser
from models.pin_mapping import PinMapping

logger = logging.getLogger(__name__)


def generate_symbol(
    raw_cad_data: Dict[str, Any], sym_dir: str
) -> Optional[Tuple[Symbol, PinMapping]]:
    """
    Parses raw EasyEDA data, generates a canonical Symbol, and serializes
    a consolidated version to a LibrePCB S-expression file.

    Returns a tuple containing:
    - The consolidated Symbol object (for component generation).
    - A PinMapping object with all original pins (for device generation).
    """
    if not raw_cad_data or not raw_cad_data.get("dataStr"):
        logger.warning("No dataStr found in raw CAD data. Skipping symbol generation.")
        return None, None

    try:
        # Step 1: Parse the EasyEDA data into a canonical Symbol object with all pins
        logger.info("Parsing EasyEDA symbol data...")
        symbol_parser = EasyEDASymbolParser()
        # The parser returns a tuple: (symbol_object, list_of_pin_data)
        symbol, pin_data_list = symbol_parser.parse_easyeda_symbol(raw_cad_data)
        if not symbol:
            logger.error("Failed to parse symbol data from EasyEDA JSON.")
            return None, None
        logger.info(f"Successfully parsed symbol: {symbol.name}")

        # Step 2: Create the PinMapping from the rich pin data list
        pin_mapping = PinMapping(pins=pin_data_list)

        # Step 3: Consolidate duplicate pins in-place for the .lp file version
        logger.info("Consolidating duplicate pins for LibrePCB symbol file...")
        _consolidate_duplicate_pins(symbol)

        # Step 4: Serialize the consolidated symbol to a LibrePCB file
        logger.info("Serializing consolidated symbol to LibrePCB format...")
        parent_dir = Path(*Path(sym_dir).parts[0:-1])
        symbol.serialize(parent_dir)

        logger.info(f"Successfully serialized symbol to {sym_dir}/symbol.lp")

        # Step 5: Return both the consolidated symbol and the full pin mapping
        return symbol, pin_mapping

    except KeyboardInterrupt:
        logger.info("\nProcess interrupted by user during symbol generation. Exiting.")
        raise
    except Exception as e:
        logger.error(f"An error occurred during symbol generation: {e}", exc_info=True)
        return None, None


def _consolidate_duplicate_pins(symbol: Symbol) -> None:
    """
    Modifies a Symbol object in-place to consolidate duplicate pin names.
    """
    unique_pins = {}
    consolidated_pins = []
    for pin in symbol.pins:
        pin_name = pin.name.value
        if pin_name not in unique_pins:
            unique_pins[pin_name] = pin
            consolidated_pins.append(pin)
        else:
            logger.info(f"  Consolidating duplicate pin: {pin_name}")
    symbol.pins = consolidated_pins
