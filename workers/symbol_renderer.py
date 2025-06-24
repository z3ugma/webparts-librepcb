# workers/symbol_renderer.py
import logging
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import List, Optional, Tuple

from constants import LIBREPCB_CLI_PATH, WebPartsFilename
from models.elements import LibrePCBElement
from models.library_part import LibraryPart
from svg_utils import render_svg_file_to_png_file

logger = logging.getLogger(__name__)


def render_and_check_symbol(
    part: LibraryPart,
) -> Tuple[Optional[str], List[Tuple[str, str, int]]]:
    """
    Runs `librepcb-cli` to both check and export the symbol image.
    """
    if not part or not part.symbol or not part.symbol.uuid:
        logger.error("Invalid LibraryPart provided to symbol renderer.")
        return None, []

    sym_dir = LibrePCBElement.SYMBOL.dir / part.symbol.uuid
    sym_dir_path = str(sym_dir)

    svg_output_path = sym_dir / WebPartsFilename.RENDERED_SVG.value
    png_output_path = sym_dir / WebPartsFilename.RENDERED_PNG.value

    command = [
        LIBREPCB_CLI_PATH,
        "open-symbol",
        sym_dir_path,
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
        raw_messages = [
            (msg.strip(), severity) for severity, msg in pattern.findall(output)
        ]

        # --- Deduplicate and Count Messages ---
        message_counts = Counter(raw_messages)
        processed_messages = [
            (msg, sev, count) for (msg, sev), count in message_counts.items()
        ]

        if not svg_output_path.exists():
            logger.error("CLI command ran, but output SVG was not created.")
            return None, processed_messages

        # --- Convert SVG to PNG ---
        logger.info(f"Converting {svg_output_path} to {png_output_path}...")
        render_svg_file_to_png_file(str(svg_output_path), str(png_output_path))
        if not png_output_path.exists():
            logger.error("SVG to PNG conversion failed.")
            return None, processed_messages

        logger.info(f"Successfully rendered and checked {sym_dir.name}.")
        return str(png_output_path.resolve()), processed_messages
    except FileNotFoundError:
        logger.error(f"The 'librepcb-cli' not found at '{LIBREPCB_CLI_PATH}'")
        return None, []
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        return None, []
