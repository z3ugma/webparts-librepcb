import logging
import subprocess
from pathlib import Path

from constants import LIBRARY_DIR, LIBREPCB_CLI_PATH, WebPartsFilename
from svg_utils import render_svg_file_to_png_file

logger = logging.getLogger(__name__)


def render_footprint_sync(package_dir: Path) -> str:
    """
    Synchronously renders a footprint to a high-resolution PNG using librepcb-cli and pyvips.
    Returns the absolute path to the rendered PNG on success, or raises an Exception on failure.
    """
    logger.info(f"--- Starting High-Res Footprint Rendering for {package_dir.name} ---")
    try:
        package_dir.mkdir(parents=True, exist_ok=True)

        svg_output_path = Path(package_dir, WebPartsFilename.RENDERED_SVG.value)
        png_output_path = Path(package_dir, WebPartsFilename.RENDERED_PNG.value)

        # Step 1: Use librepcb-cli to generate the source SVG.
        cli_args = [
            LIBREPCB_CLI_PATH,
            "open-package",
            str(package_dir),
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

        # Step 2: Convert the generated SVG to a high-resolution PNG using pyvips.
        render_svg_file_to_png_file(str(svg_output_path), str(png_output_path))

        logger.info("--- PNG Conversion Succeeded ---")

        # Return the absolute path to the final PNG for clarity and robustness.
        return str(png_output_path.resolve())

    except Exception as e:
        logger.error(f"--- Footprint Rendering Failed ---\n{e}")
        raise
