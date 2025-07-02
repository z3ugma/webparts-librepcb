import io
import logging
import xml.etree.ElementTree as ET
from typing import NamedTuple, Tuple

import cairosvg
from PIL import Image

from constants import IMAGE_DIMENSIONS

logger = logging.getLogger(__name__)

# SVG namespace
SVG_NAMESPACE = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NAMESPACE)


class SvgInfo(NamedTuple):
    """Information about an SVG file."""

    viewbox_x: float
    viewbox_y: float
    viewbox_width: float
    viewbox_height: float


class PngInfo(NamedTuple):
    """Information about a PNG file."""

    width: int
    height: int


def parse_svg_viewbox(svg_path: str) -> SvgInfo:
    """
    Parse SVG file and extract viewBox information.

    Args:
        svg_path: Path to SVG file

    Returns:
        SvgInfo with viewBox data

    Raises:
        ValueError: If viewBox is missing or invalid
    """
    tree = ET.parse(svg_path)
    root = tree.getroot()
    viewbox = root.get("viewBox")

    if not viewbox:
        raise ValueError(f"SVG file {svg_path} does not have a viewBox attribute")

    parts = viewbox.split()
    if len(parts) != 4:
        raise ValueError(f"SVG viewBox has invalid format: {viewbox}")

    try:
        return SvgInfo(
            viewbox_x=float(parts[0]),
            viewbox_y=float(parts[1]),
            viewbox_width=float(parts[2]),
            viewbox_height=float(parts[3]),
        )
    except ValueError as e:
        raise ValueError(f"SVG viewBox contains non-numeric values: {viewbox}") from e


def get_png_dimensions(png_path: str) -> PngInfo:
    """
    Get PNG file dimensions.

    Args:
        png_path: Path to PNG file

    Returns:
        PngInfo with width and height
    """
    with Image.open(png_path) as img:
        return PngInfo(width=img.size[0], height=img.size[1])


def calculate_svg_to_png_scale(svg_info: SvgInfo, png_info: PngInfo) -> float:
    """
    Calculate scale factor from SVG viewBox to PNG pixels.

    Args:
        svg_info: SVG viewBox information
        png_info: PNG dimension information

    Returns:
        Scale factor (maintains aspect ratio using minimum scale)
    """
    scale_x = png_info.width / svg_info.viewbox_width
    scale_y = png_info.height / svg_info.viewbox_height
    return min(scale_x, scale_y)


def load_svg_tree(svg_path: str) -> Tuple[ET.ElementTree, ET.Element]:
    """
    Load SVG file and return tree and root element.

    Args:
        svg_path: Path to SVG file

    Returns:
        Tuple of (ElementTree, root_element)

    Raises:
        FileNotFoundError: If SVG file not found
        ET.ParseError: If SVG file is malformed
    """
    tree = ET.parse(svg_path)
    root = tree.getroot()

    # Ensure the root element is an <svg> tag in the SVG namespace
    if root.tag != ET.QName(SVG_NAMESPACE, "svg"):
        # Attempt to find an svg tag if it's wrapped
        svg_element = root.find(f".//{{{SVG_NAMESPACE}}}svg")
        if svg_element is not None:
            logger.warning("Found <svg> element deeper in XML structure")
            root = svg_element
        else:
            raise ValueError(f"No <svg> element found in {svg_path}")

    return tree, root


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
        final_png_info = get_png_dimensions(png_path)
        logger.info(
            f"Successfully rendered PNG. Final dimensions: {final_png_info.width}x{final_png_info.height}"
        )

    except Exception as e:
        logger.error(f"Failed to render SVG with cairosvg: {e}")
        raise


def create_coordinate_mapper(
    svg_info: SvgInfo,
    png_info: PngInfo,
    source_offset_x: float,
    source_offset_y: float,
    unit_scale: float = 0.254,
):
    """
    Create a coordinate mapper function for converting mm coordinates to PNG pixels.

    Args:
        svg_info: SVG viewBox information
        png_info: PNG dimension information
        source_offset_x: Source coordinate system X offset
        source_offset_y: Source coordinate system Y offset
        unit_scale: Scale factor from source units to mm (default: 0.254 for 10mil units)

    Returns:
        Function that maps (mm_x, mm_y) -> (png_x, png_y)
    """
    svg_to_png_scale = calculate_svg_to_png_scale(svg_info, png_info)

    def coordinate_mapper(mm_x: float, mm_y: float) -> Tuple[float, float]:
        """Convert mm coordinates to PNG pixel coordinates."""
        # Convert to source units and add offset
        svg_x = (mm_x / unit_scale) + source_offset_x
        svg_y = (mm_y / unit_scale) + source_offset_y

        # Convert to PNG pixel coordinates
        png_x = (svg_x - svg_info.viewbox_x) * svg_to_png_scale
        png_y = (svg_y - svg_info.viewbox_y) * svg_to_png_scale

        return png_x, png_y

    return coordinate_mapper


def overlay_alignment_crosshairs(
    png_path: str, alignment, output_path: str = None
) -> str:
    """
    Overlay alignment crosshairs on a PNG image.

    Args:
        png_path: Path to source PNG file
        alignment: FootprintAlignment object with reference points
        output_path: Path for output PNG (defaults to overwriting input)

    Returns:
        Path to the output file
    """
    from PIL import Image, ImageDraw

    if output_path is None:
        output_path = png_path

    # Load the image
    img = Image.open(png_path)
    draw = ImageDraw.Draw(img)

    # Use bright colors that contrast with typical footprint colors
    colors = ["cyan", "magenta", "lime", "orange"]

    for i, ref in enumerate(alignment.reference_points):
        color = colors[i % len(colors)]
        x, y = ref.source_x, ref.source_y

        # Draw crosshair (larger and more visible than test version)
        crosshair_size = 20
        line_width = 1

        # Horizontal line
        draw.line(
            [(x - crosshair_size, y), (x + crosshair_size, y)],
            fill=color,
            width=line_width,
        )
        # Vertical line
        draw.line(
            [(x, y - crosshair_size), (x, y + crosshair_size)],
            fill=color,
            width=line_width,
        )
        # Center dot
        dot_size = 3
        draw.ellipse(
            [(x - dot_size, y - dot_size), (x + dot_size, y + dot_size)], fill=color
        )

        # Add label with pad number and coordinates
        pad_name = ref.pad_number.split("_")[0]  # Extract pad number without corner
        label_offset = 25
        # Include both pixel and MM coordinates like the test script had
        label_text = f"{pad_name}\n({ref.source_x:.0f},{ref.source_y:.0f})\n({ref.target_x:.3f},{ref.target_y:.3f})"
        draw.text((x + label_offset, y - label_offset), label_text, fill=color)

    # Save the modified image
    img.save(output_path)
    logger.info(
        f"Overlaid {len(alignment.reference_points)} alignment crosshairs on {output_path}"
    )

    return output_path


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
