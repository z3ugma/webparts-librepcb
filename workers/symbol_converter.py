import logging
from typing import Dict, Any

from adapters.easyeda.easyeda_symbol import EasyEDASymbolParser
from adapters.librepcb.librepcb_symbol import LibrePCBSymbolSerializer
from models.symbol import Symbol

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
        canonical_symbol = symbol_parser.parse_easyeda_symbol(raw_cad_data)
        if not canonical_symbol:
            logger.error("Failed to parse symbol data from EasyEDA JSON.")
            return False
        logger.info(f"Successfully parsed symbol: {canonical_symbol.name}")

        # Step 2: Serialize the canonical Symbol object to a LibrePCB file
        logger.info("Serializing symbol to LibrePCB format...")
        librepcb_serializer = LibrePCBSymbolSerializer(invert_y=True)
        librepcb_serializer.serialize_to_file(canonical_symbol, sym_dir)
        logger.info(f"Successfully serialized symbol to {sym_dir}/symbol.lp")

        return True

    except Exception as e:
        logger.error(f"An error occurred during symbol generation: {e}", exc_info=True)
        return False
