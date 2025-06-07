# Global imports
import logging
import xml.etree.ElementTree as ET
from typing import List

import cairosvg
from PySide6.QtCore import QSize
from models.footprint import Pad

logger = logging.getLogger(__name__)

SVG_NAMESPACE = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NAMESPACE)


def add_pad_numbers_to_svg(svg_data: bytes, pads: List[Pad]) -> bytes:
    """
    Adds text elements for pad numbers to the given SVG data.
    """
    try:
        root = ET.fromstring(svg_data)
        pad_numbers_group_id = "pcbPadNumbers"
        # Find existing group or create a new one
        pad_numbers_group = root.find(f".//{{{SVG_NAMESPACE}}}g[@id='{pad_numbers_group_id}']")
        if pad_numbers_group is None:
            pad_numbers_group = ET.Element(ET.QName(SVG_NAMESPACE, "g"))
            pad_numbers_group.set("id", pad_numbers_group_id)
            root.append(pad_numbers_group)
        else:
            pad_numbers_group.clear()  # Clear existing numbers to prevent duplicates

        for pad in pads:
            text_node = ET.Element(ET.QName(SVG_NAMESPACE, "text"))
            text_node.set("x", str(pad.position.x))
            text_node.set("y", str(pad.position.y))
            text_node.set("font-family", "Verdana, Arial, sans-serif")
            text_node.set("fill", "white")
            text_node.set("text-anchor", "middle")
            text_node.set("font-size", "2")  # Increased font size for visibility
            text_node.set("dominant-baseline", "central")
            text_node.set("style", "pointer-events: none; font-weight: bold;")
            text_node.text = pad.number
            pad_numbers_group.append(text_node)
        return ET.tostring(root, encoding="utf-8")
    except ET.ParseError as e:
        logger.error(f"Error adding pad numbers to SVG: {e}")
        return svg_data


def render_svg_to_png_bytes(svg_data: bytes, output_size: QSize) -> bytes:
    """
    Renders SVG data to PNG byte data using CairoSVG.
    """
    try:
        return cairosvg.svg2png(
            bytestring=svg_data,
            output_width=output_size.width(),
            output_height=output_size.height(),
        )
    except Exception as e:
        logger.error(f"CairoSVG rendering failed: {e}")
        return b""
