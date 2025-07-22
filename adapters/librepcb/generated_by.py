import logging
from typing import Optional
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


def create_generated_by_string(source: str, identifier: str) -> str:
    """
    Creates a LibrePCB 'generated_by' string.

    Args:
        source: The source of the element (e.g., 'webparts', 'lcsc').
        identifier: The unique identifier for the element (e.g., LCSC part number).

    Returns:
        The formatted 'generated_by' string.
    """
    return f'(generated_by "{source}:{identifier}")'


def find_element_by_generated_by(
    search_dir: Path, source: str, identifier: str
) -> Optional[uuid.UUID]:
    """
    Finds a LibrePCB element by its 'generated_by' string in a directory.

    Args:
        search_dir: The directory to search for element directories.
        source: The source of the element (e.g., 'webparts', 'lcsc').
        identifier: The unique identifier for the element.

    Returns:
        The UUID of the found element, or None if not found.
    """
    if not search_dir.is_dir():
        return None

    expected_string = f'"{source}:{identifier}"'
    logger.info(
        f"Searching for element with '{expected_string}' in '{search_dir}'..."
    )

    for subdir in search_dir.iterdir():
        if not subdir.is_dir():
            continue

        for lp_file in subdir.glob("*.lp"):
            try:
                with open(lp_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if "generated_by" in line and expected_string in line:
                            try:
                                found_uuid = uuid.UUID(subdir.name)
                                logger.info(f"  ✅ Found existing element with UUID: {found_uuid}")
                                return found_uuid
                            except ValueError:
                                continue
            except IOError:
                continue

    logger.info(f"  ❌ No existing element found for '{identifier}'.")
    return None
