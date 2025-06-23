import io
import logging

import cairosvg
from PIL import Image

from constants import IMAGE_DIMENSIONS

logger = logging.getLogger(__name__)


def render_svg_file_to_png_file(svg_path: str, png_path: str):
    """
    Renders an SVG file to a high-resolution PNG, dynamically calculating the
    scale factor to fit within the target dimensions defined in constants.
    This version uses cairosvg for rendering.
    """
    try:
        # Step 1: Get the natural size by rendering the SVG at scale=1.0 to memory
        logger.info(f"Probing natural size of {svg_path} using cairosvg")
        probe_png_data = cairosvg.svg2png(url=svg_path, scale=1.0)

        # Use Pillow to read the dimensions of the in-memory PNG
        with Image.open(io.BytesIO(probe_png_data)) as probe_image:
            natural_width, natural_height = probe_image.size
        logger.info(f"Natural SVG dimensions: {natural_width}x{natural_height}")

        # Step 2: Calculate the required scale factor to fit within target dimensions
        target_dim = IMAGE_DIMENSIONS
        scale_x = target_dim / natural_width if natural_width > 0 else 0
        scale_y = target_dim / natural_height if natural_height > 0 else 0

        # Use the smaller scale factor to ensure the entire image fits
        scale_factor = min(scale_x, scale_y) if min(scale_x, scale_y) > 0 else 1.0

        logger.info(
            f"Calculated scale factor of {scale_factor:.2f} to fit within {target_dim}px."
        )

        # Step 3: Render the final image using the calculated scale factor
        logger.info(f"Rendering {svg_path} to {png_path} with calculated scale.")
        cairosvg.svg2png(url=svg_path, write_to=png_path, scale=scale_factor)

        # Verify final dimensions
        with Image.open(png_path) as final_image:
            final_width, final_height = final_image.size
        logger.info(
            f"Successfully rendered PNG. Final dimensions: {final_width}x{final_height}"
        )

    except Exception as e:
        logger.error(f"Failed to render SVG with cairosvg: {e}")
        raise


if __name__ == "__main__":
    # --- Logger Setup ---
    # This configures the root logger to print messages to the console.
    # It will capture logs from this script and any other modules that use logging.
    log_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Configure a handler to stream logs to the console (stdout)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(log_formatter)

    # Get the root logger, add the handler, and set the logging level
    root_logger = logging.getLogger()
    root_logger.addHandler(stream_handler)
    root_logger.setLevel(logging.INFO)

    # --- Test Execution ---
    # Now that logging is configured, run the test functions.
    logger.info("Starting SVG rendering test...")
    for part in ["footprint", "rendered"]:
        svg_path = f"WebParts.lplib/pkg/39e1b05b-30bd-4c64-a6c9-a1b67d9eb207/{part}.svg"
        png_path = f"WebParts.lplib/pkg/39e1b05b-30bd-4c64-a6c9-a1b67d9eb207/{part}.png"
        render_svg_file_to_png_file(svg_path, png_path)
    logger.info("SVG rendering test finished.")
