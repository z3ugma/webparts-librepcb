import logging
import subprocess
from pathlib import Path

from constants import LIBREPCB_CLI_PATH, WebPartsFilename
from svg_utils import render_svg_file_to_png_file

logger = logging.getLogger(__name__)


def render_symbol_sync(symbol_dir: Path) -> str:
    """
    Synchronously renders a symbol to a high-resolution PNG.
    """
    logger.info(f"--- Starting High-Res Symbol Rendering for {symbol_dir.name} ---")
    try:
        symbol_dir.mkdir(parents=True, exist_ok=True)

        svg_output_path = symbol_dir / WebPartsFilename.RENDERED_SVG.value
        png_output_path = symbol_dir / WebPartsFilename.RENDERED_PNG.value

        cli_args = [
            LIBREPCB_CLI_PATH,
            "open-symbol",
            str(symbol_dir),
            "--export",
            str(svg_output_path),
        ]

        p = subprocess.Popen(
            cli_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        stdout, stderr = p.communicate()

        if stdout:
            logger.info(f"librepcb-cli stdout:\n{stdout}")
        if stderr:
            logger.warning(f"librepcb-cli stderr:\n{stderr}")

        if p.returncode != 0:
            raise RuntimeError(f"librepcb-cli failed with return code {p.returncode}")

        if not svg_output_path.exists():
            raise FileNotFoundError(f"SVG file was not created at {svg_output_path}")

        logger.info("--- SVG Generation Succeeded ---")

        render_svg_file_to_png_file(str(svg_output_path), str(png_output_path))

        logger.info("--- PNG Conversion Succeeded ---")

        return str(png_output_path.resolve())

    except Exception as e:
        logger.error(f"--- Symbol Rendering Failed ---\n{e}")
        raise
