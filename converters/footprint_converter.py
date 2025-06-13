import logging
from typing import Dict, Any

from adapters.easyeda.easyeda_footprint import EasyEDAParser
from adapters.librepcb.librepcb_footprint import LibrePCBFootprintSerializer
from models.footprint import Footprint

logger = logging.getLogger(__name__)

def generate_footprint(raw_cad_data: Dict[str, Any], pkg_dir: str) -> bool:
    """
    Parses raw EasyEDA data, generates a canonical Footprint, and serializes
    it to a LibrePCB S-expression file.

    Args:
        raw_cad_data: The raw dictionary data from the EasyEDA API.
        pkg_dir: The target directory path to save the 'package.lp' file.

    Returns:
        True if the generation was successful, False otherwise.
    """
    if not raw_cad_data or not raw_cad_data.get("packageDetail"):
        logger.warning("No packageDetail found in raw CAD data. Skipping footprint generation.")
        return False

    try:
        # Step 1: Parse the EasyEDA data into a canonical Footprint object
        logger.info("Parsing EasyEDA footprint data...")
        easyeda_parser = EasyEDAParser()
        canonical_footprint = easyeda_parser.parse_easyeda_json(raw_cad_data)
        if not canonical_footprint:
            logger.error("Failed to parse footprint data from EasyEDA JSON.")
            return False
        logger.info(f"Successfully parsed footprint: {canonical_footprint.name}")

        # Step 2: Serialize the canonical Footprint object to a LibrePCB file
        logger.info("Serializing footprint to LibrePCB format...")
        librepcb_serializer = LibrePCBFootprintSerializer(invert_y=True)
        librepcb_serializer.serialize_to_file(canonical_footprint, pkg_dir)
        logger.info(f"Successfully serialized footprint to {pkg_dir}/package.lp")
        
        return True

    except Exception as e:
        logger.error(f"An error occurred during footprint generation: {e}", exc_info=True)
        return False
