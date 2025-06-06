# Global imports
import argparse
import logging
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

# Define the SVG namespace
SVG_NAMESPACE = "http://www.w3.org/2000/svg"

# Register the default SVG namespace to avoid 'ns0:' prefixes in the output
# This makes the output SVG cleaner.
ET.register_namespace("", SVG_NAMESPACE)


def add_pad_numbers_to_svg_file(input_svg_path):
    """
    Reads an SVG file, adds text elements for pad numbers based on 'c_partid="part_pad"'
    elements, and saves the modified SVG to a new file.
    """
    try:
        tree = ET.parse(input_svg_path)
        root = tree.getroot()
    except FileNotFoundError:
        logger.error(f"Error: Input SVG file not found at '{input_svg_path}'")
        return
    except ET.ParseError as e:
        logger.error(f"Error parsing SVG file '{input_svg_path}': {e}")
        return

    # Ensure the root element is an <svg> tag in the SVG namespace
    if root.tag != ET.QName(SVG_NAMESPACE, "svg"):
        logger.error(f"Error: The root element in '{input_svg_path}' is not <svg>.")
        # Attempt to find an svg tag if it's wrapped, e.g. in an XML document
        # This is a basic check; a more robust solution might be needed for complex non-SVG XML wrappers.
        svg_element_found = root.find(f".//{{{SVG_NAMESPACE}}}svg")
        if svg_element_found is not None:
            logger.warning(
                "Warning: Found an <svg> element deeper in the XML structure. "
                "The script will attempt to process this, but the output will be the entire modified input XML."
            )
            # For simplicity, we'll modify in place. If only the SVG part needs to be extracted and saved,
            # the logic would need to change to create a new tree with just the modified SVG element.
            root = svg_element_found  # Re-assign root to the found SVG element for processing
        # This means we are now operating within that SVG sub-tree.
        # When saving, 'tree.write' will still write the original tree structure
        # with modifications inside this sub-tree.
        # If the goal is a *new* SVG file containing *only* the modified <svg>
        # and its children, then a new ET.ElementTree(modified_svg_element)
        # would need to be created before writing.
        # For now, we modify the original tree.
        else:
            logger.error("No <svg> element found. Cannot process.")
            return

    # Find or create the group for pad numbers
    pad_numbers_group_id = "pcbPadNumbers"
    # Search for the group as a direct child of the current root (which should be <svg>)
    pad_numbers_group = root.find(f"{{{SVG_NAMESPACE}}}g[@id='{pad_numbers_group_id}']")

    if pad_numbers_group is None:
        # Create the group if it doesn't exist, using the SVG namespace
        pad_numbers_group = ET.Element(ET.QName(SVG_NAMESPACE, "g"))
        pad_numbers_group.set("id", pad_numbers_group_id)
        root.append(pad_numbers_group)  # Append to the <svg> element
        logger.info(f"Created <g id='{pad_numbers_group_id}'>")
    else:
        # Optional: Clear existing numbers if the script might be run multiple times
        # on an already processed file. For this example, we'll append.
        # for child in list(pad_numbers_group):
        #     pad_numbers_group.remove(child)
        logger.info(
            f"Found existing <g id='{pad_numbers_group_id}'>. Appending new numbers."
        )

    pads_found_count = 0
    # Find all <g c_partid="part_pad"> elements anywhere within the <svg> root
    for pad_element in root.findall(f".//{{{SVG_NAMESPACE}}}g[@c_partid='part_pad']"):
        pads_found_count += 1
        origin_str = pad_element.get("c_origin")
        number_str = pad_element.get("number")  # This is the "pin name/number"

        if origin_str and number_str:
            try:
                x_str, y_str = origin_str.split(",")
                x = float(x_str)  # Using float for precision
                y = float(y_str)
            except ValueError:
                logger.warning(
                    f"Warning: Could not parse c_origin '{origin_str}' for pad {number_str}. Skipping."
                )
                continue

            # Create the <text> element using the SVG namespace
            text_node = ET.Element(ET.QName(SVG_NAMESPACE, "text"))

            # Set coordinates
            text_node.set("x", str(x))
            text_node.set("y", str(y))

            # Apply styling attributes similar to your web template
            text_node.set("font-family", "Verdana, Arial, sans-serif")
            text_node.set("fill", "white")  # Assumes a dark PCB background
            text_node.set("text-anchor", "middle")
            text_node.set(
                "font-size", "1"
            )  # This size is relative to the SVG's coordinate system/viewBox
            text_node.set("dominant-baseline", "central")
            # Add font-weight: bold from your web CSS and pointer-events: none
            text_node.set("style", "pointer-events: none; font-weight: bold;")

            text_node.text = number_str  # Set the actual pad number as the text content

            pad_numbers_group.append(text_node)
            # print(f"Added text for pad {number_str} at ({x}, {y})")
        else:
            if not origin_str:
                logger.warning(
                    f"Warning: Pad element (processed count: {pads_found_count}) missing 'c_origin'. Skipping."
                )
            if not number_str:
                logger.warning(
                    f"Warning: Pad element (processed count: {pads_found_count}) missing 'number'. Skipping."
                )

    if pads_found_count == 0:
        logger.warning(
            "Warning: No pad elements with c_partid='part_pad' found in the SVG."
        )
    else:
        logger.info(f"Processed {pads_found_count} pad elements.")

    # Pretty print the XML tree (requires Python 3.9+)
    # This modifies the tree in-place.
    if hasattr(ET, "indent"):
        ET.indent(tree)  # Pass the ElementTree object

    try:
        # Write the modified tree to the output file
        output_svg_path = f"{input_svg_path}.text.svg"
        tree.write(output_svg_path, encoding="utf-8", xml_declaration=True)
        logger.info(f"Successfully wrote modified SVG to '{output_svg_path}'")
    except IOError as e:
        logger.error(f"Error writing SVG to '{output_svg_path}': {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Adds pad numbers as text elements to an SVG file."
    )
    parser.add_argument(
        "input_svg", help="Path to the input SVG file (e.g., the PCB footprint SVG)."
    )

    args = parser.parse_args()

    add_pad_numbers_to_svg_file(args.input_svg)


if __name__ == "__main__":
    main()
