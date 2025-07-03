# workers/element_renderer.py
import logging
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import List, Optional, Tuple

from constants import LIBREPCB_CLI_PATH, WebPartsFilename
from models.library_part import LibraryPart
from models.elements import LibrePCBElement
from models.status import ValidationMessage, ValidationSeverity, ValidationSource
from svg_utils import render_svg_file_to_png_file

logger = logging.getLogger(__name__)


def render_and_check_element(
    part: LibraryPart,
    element_type: LibrePCBElement,
) -> Tuple[Optional[str], List[ValidationMessage]]:
    """
    Runs `librepcb-cli` to both check and export an element's image.
    """
    if not part:
        logger.error("Invalid LibraryPart provided to renderer.")
        return None, []

    element_info = None
    if element_type == LibrePCBElement.PACKAGE:
        element_info = part.footprint
        cli_command = "open-package"
    elif element_type == LibrePCBElement.SYMBOL:
        element_info = part.symbol
        cli_command = "open-symbol"
    else:
        logger.error(f"Unsupported element type: {element_type}")
        return None, []

    if not element_info or not element_info.uuid:
        logger.error(f"Invalid {element_type.value} data in LibraryPart.")
        return None, []

    element_dir = element_type.dir / element_info.uuid
    element_dir_path = str(element_dir)

    svg_output_path = element_dir / WebPartsFilename.RENDERED_SVG.value
    png_output_path = element_dir / WebPartsFilename.RENDERED_PNG.value

    command = [
        LIBREPCB_CLI_PATH,
        cli_command,
        element_dir_path,
        "--check",
        "--export",
        str(svg_output_path),
    ]

    logger.info(f"Running command: {' '.join(command)}")

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )

        output = result.stdout + result.stderr
        logger.debug(f"CLI Output:\n{output}")

        if result.returncode != 0 and "Finished with errors!" not in output:
            logger.error(f"LibrePCB-CLI failed unexpectedly:\n{output}")
            return None, []

        # --- Parse Messages ---
        pattern = re.compile(r"-\s*\[(WARNING|HINT|ERROR)\]\s*(.*)")
        messages = [
            ValidationMessage(
                message=msg.strip(),
                severity=ValidationSeverity(severity),
                source=ValidationSource.LIBREPCB,
            )
            for severity, msg in pattern.findall(output)
        ]

        if not svg_output_path.exists():
            logger.error("CLI command ran, but output SVG was not created.")
            return None, messages

        # --- Convert SVG to PNG ---
        logger.info(f"Converting {svg_output_path} to {png_output_path}...")
        render_svg_file_to_png_file(str(svg_output_path), str(png_output_path))
        if not png_output_path.exists():
            logger.error("SVG to PNG conversion failed.")
            return None, messages

        logger.info(f"Successfully rendered and checked {element_dir.name}.")
        return str(png_output_path.resolve()), messages
    except FileNotFoundError:
        logger.error(f"The 'librepcb-cli' not found at '{LIBREPCB_CLI_PATH}'")
        return None, []
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        return None, []
