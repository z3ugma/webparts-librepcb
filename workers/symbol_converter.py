import logging
from pathlib import Path
from typing import Any, Dict

from librepcb_parts_generator.entities.symbol import Symbol

from adapters.easyeda.easyeda_symbol import EasyEDASymbolParser

logger = logging.getLogger(__name__)


def generate_symbol(raw_cad_data: Dict[str, Any], sym_dir: str) -> bool:
    """
    Parses raw EasyEDA data, generates a canonical Symbol, and serializes
    it to a LibrePCB S-expression file.

    Args:
        raw_cad_data: The raw dictionary data from the EasyEDA API.
        sym_dir: The target directory path to save the 'symbol.lp' file.

    Returns:
        True if the generation was successful, False otherwise.
    """
    if not raw_cad_data or not raw_cad_data.get("dataStr"):
        logger.warning("No dataStr found in raw CAD data. Skipping symbol generation.")
        return False

    try:
        # Step 1: Parse the EasyEDA data into a canonical Symbol object
        logger.info("Parsing EasyEDA symbol data...")
        symbol_parser = EasyEDASymbolParser()
        symbol = symbol_parser.parse_easyeda_symbol(raw_cad_data)
        if not symbol:
            logger.error("Failed to parse symbol data from EasyEDA JSON.")
            return False
        logger.info(f"Successfully parsed symbol: {symbol.name}")

        # Step 2: Serialize the canonical Symbol object to a LibrePCB file
        logger.info("Serializing symbol to LibrePCB format...")
        symbol = _consolidate_duplicate_pins(symbol)
        parent_dir = Path(*Path(sym_dir).parts[0:-1])
        symbol.serialize(parent_dir)
        logger.info(f"Successfully serialized symbol to {sym_dir}/symbol.lp")

        return True

    except KeyboardInterrupt:
        logger.info("\nProcess interrupted by user during symbol generation. Exiting.")
        raise
    except Exception as e:
        logger.error(f"An error occurred during symbol generation: {e}", exc_info=True)
        return False


def _consolidate_duplicate_pins(symbol: Symbol) -> Symbol:
    """Consolidate duplicate pin names into single pins, following LibrePCB best practices."""
    unique_pins = {}
    consolidated_pins = []

    for pin in symbol.pins:
        pin_name = pin.name.value

        if pin_name in unique_pins:
            # Pin name already exists, skip this duplicate
            # In LibrePCB, multiple physical pins with same function
            # are handled in the device editor, not the symbol
            print(f"  Consolidating duplicate pin: {pin_name}")
            continue
        else:
            # First occurrence of this pin name, keep it
            unique_pins[pin_name] = pin
            consolidated_pins.append(pin)

    symbol.pins = consolidated_pins
    return symbol
