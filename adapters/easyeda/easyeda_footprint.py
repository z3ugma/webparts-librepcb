# Global imports
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID, uuid4

from models.footprint import (  # Relative import if in a package; from footprint_model import ( # Or direct if in the same folder and you add to sys.path
    Drill,
    DrillShape,
    Footprint,
    Model3D,
    Pad,
    PadShape,
    PadType,
)
from models.graphics import (
    Arc,
    Circle,
    GraphicElement,
    Line,
    Point,
    Polygon,
    Polyline,
    Rectangle,
    Text,
    TextAlignHorizontal,
    TextAlignVertical,
)
from models.layer import LayerRef, LayerType

# Assuming your Pydantic models (Footprint, Pad, Point, Line, LayerType, LayerRef, etc.)
# are in a file named footprint_model.py


# --- SVG Path Parsing (Simplified for M, L, H, V, Z) ---
# For full SVG arc (A) to center-point conversion, a more robust library or implementation is needed.
# For now, we'll focus on simpler paths and leave Arc parsing as a TODO if complex.


def parse_svg_path_to_points(
    path_str: str, offset_x: float, offset_y: float, unit_scale: float
) -> List[Point]:
    points: List[Point] = []

    # Normalize path: remove extra spaces around commands and commas
    path_str = re.sub(
        r"\s*([MLHVZ])\s*", r"\1", path_str, flags=re.IGNORECASE
    )  # Remove space around commands
    path_str = re.sub(r"\s*,\s*", ",", path_str)  # Normalize commas
    path_str = path_str.replace(
        ",", " "
    )  # Replace commas with spaces for easier splitting

    # Split into command and coordinate groups
    # This regex captures a command (M, L, H, V, Z) and the string of coordinates that follows
    # until the next command or end of string.
    command_groups = re.findall(r"([MLHVZ])([^MLHVZ]*)", path_str, flags=re.IGNORECASE)

    current_x, current_y = 0.0, 0.0
    start_x, start_y = 0.0, 0.0  # For 'Z' command

    for i, (command_char, coords_segment) in enumerate(command_groups):
        coords_str = coords_segment.strip()
        raw_coords = [float(c) for c in coords_str.split()] if coords_str else []

        is_relative = command_char.islower()
        command = command_char.upper()

        if command == "M":  # Moveto
            for j in range(0, len(raw_coords), 2):
                px, py = raw_coords[j], raw_coords[j + 1]
                if is_relative and points:  # Relative moveto (after first point)
                    current_x += px
                    current_y += py
                else:  # Absolute moveto or first moveto
                    current_x = px
                    current_y = py

                scaled_x = current_x * unit_scale - offset_x
                scaled_y = current_y * unit_scale - offset_y
                points.append(Point(x=scaled_x, y=scaled_y))
                if i == 0 and j == 0:  # Store first point for potential 'Z'
                    start_x, start_y = scaled_x, scaled_y

        elif command == "L":  # Lineto
            for j in range(0, len(raw_coords), 2):
                px, py = raw_coords[j], raw_coords[j + 1]
                if is_relative:
                    current_x += px
                    current_y += py
                else:
                    current_x, current_y = px, py
                points.append(
                    Point(
                        x=current_x * unit_scale - offset_x,
                        y=current_y * unit_scale - offset_y,
                    )
                )

        elif command == "H":  # Horizontal lineto
            for val in raw_coords:
                if is_relative:
                    current_x += val
                else:
                    current_x = val
                points.append(
                    Point(
                        x=current_x * unit_scale - offset_x,
                        y=current_y * unit_scale - offset_y,
                    )
                )

        elif command == "V":  # Vertical lineto
            for val in raw_coords:
                if is_relative:
                    current_y += val
                else:
                    current_y = val
                points.append(
                    Point(
                        x=current_x * unit_scale - offset_x,
                        y=current_y * unit_scale - offset_y,
                    )
                )

        elif command == "Z":  # ClosePath
            if points and (points[-1].x != start_x or points[-1].y != start_y):
                points.append(Point(x=start_x, y=start_y))
            # After Z, the path is closed. A new M should follow if path continues.
            # For simple polygons, this is usually the end.
            current_x, current_y = (
                start_x / unit_scale,
                start_y / unit_scale,
            )  # Reset current point to start

    return points


# Placeholder for SVG Arc to Center-Point conversion (Complex)
def convert_svg_arc_to_center_params(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    fa: bool,
    fs: bool,
    rx: float,
    ry: float,
    phi_degrees: float,
    offset_x: float,
    offset_y: float,
    unit_scale: float,
) -> Tuple[Point, float, float, float]:  # center, radius_x, start_angle, sweep_angle
    # This is a non-trivial conversion.
    # See: https://www.w3.org/TR/SVG/implnote.html#ArcImplementationNotes
    # For now, returning dummy values.
    # A proper implementation would involve matrix math and trigonometry.
    print(
        f"Warning: SVG Arc parsing is complex and not fully implemented. Shape: A {rx} {ry} {phi_degrees} {1 if fa else 0} {1 if fs else 0} {x2} {y2}"
    )
    # Using scaled coordinates for dummy values
    scaled_x1, scaled_y1 = x1 * unit_scale, y1 * unit_scale
    scaled_x2, scaled_y2 = x2 * unit_scale, y2 * unit_scale
    center_x = (scaled_x1 + scaled_x2) / 2
    center_y = (scaled_y1 + scaled_y2) / 2
    radius = ((scaled_x2 - scaled_x1) ** 2 + (scaled_y2 - scaled_y1) ** 2) ** 0.5 / 2
    return (
        Point(x=center_x, y=center_y),
        radius,
        0.0,
        180.0,
    )  # Dummy start_angle, sweep_angle


class EasyEDAParser:
    def __init__(self):
        self.layer_map: Dict[str, LayerRef] = {}
        # Store (CDM LayerType for mask, expansion value)
        self.mask_layer_properties: Dict[str, Tuple[LayerType, Optional[float]]] = {}
        self.easyeda_layer_id_to_name: Dict[str, str] = {}
        self.unit_scale = 0.254
        """
        Convert EasyEDA's internal geometric units (10 mil per unit) into millimeters.
        1 unit = 10 mil → 0.254 mm.
        The canvas 'unit' field is only for editor display (grid/snap), not for shape data.
        """

    def _parse_layer_definitions(self, layer_strings: List[str]):
        """
        Parses EasyEDA layer definitions and populates self.layer_map and self.mask_expansions.
        Example: "1~TopLayer~#FF0000~true~false~true~"
                 "7~TopSolderMaskLayer~#800080~true~false~true~0.3" (0.3 is expansion)
        """
        self.layer_map = {}
        self.mask_layer_properties = {}
        self.easyeda_layer_id_to_name = {}

        # Basic mapping from EasyEDA layer names/IDs to CDM LayerType
        # This needs to be comprehensive based on common EasyEDA usage
        name_to_cdm_type = {
            "toplayer": LayerType.TOP_COPPER,
            "bottomlayer": LayerType.BOTTOM_COPPER,
            "topsilklayer": LayerType.TOP_SILKSCREEN,
            "bottomsilklayer": LayerType.BOTTOM_SILKSCREEN,
            "toppastemasklayer": LayerType.TOP_PASTE_MASK,
            "bottompastemasklayer": LayerType.BOTTOM_PASTE_MASK,
            "topsoldermasklayer": LayerType.TOP_SOLDER_MASK,
            "bottomsoldermasklayer": LayerType.BOTTOM_SOLDER_MASK,
            "boardoutline": LayerType.BOARD_OUTLINE,  # Or COURTYARD depending on usage
            "document": LayerType.DOCUMENTATION,
            "mechanical": LayerType.MECHANICAL,  # Will require index if multiple
            "topassembly": LayerType.ASSEMBLY_TOP,
            "bottomassembly": LayerType.ASSEMBLY_BOTTOM,
            "multi-layer": LayerType.MULTI_LAYER,
            "hole": None,  # Special, not a drawing layer
            "componentshapelayer": LayerType.COURTYARD_TOP,  # A common interpretation
            "leadshapelayer": LayerType.DOCUMENTATION,  # Or specific fabrication layer
            "componentmarkinglayer": LayerType.ASSEMBLY_TOP,  # Or documentation
        }

        # Track mechanical layer indices
        mechanical_layer_count = 0

        for layer_str in layer_strings:
            parts = layer_str.split("~")
            ee_id = parts[0]
            ee_name = parts[1].lower().replace(" ", "").replace("-", "")
            self.easyeda_layer_id_to_name[ee_id] = parts[1]  # Store original name

            expansion: Optional[float] = None
            if len(parts) > 7 and parts[7]:
                try:
                    expansion = float(parts[7])
                except ValueError:
                    pass  # Not a float

            cdm_type: Optional[LayerType] = None
            cdm_index: Optional[int] = None

            if ee_name in name_to_cdm_type:
                cdm_type = name_to_cdm_type[ee_name]
            elif "inner" in ee_name:
                try:
                    idx = int(ee_name.replace("inner", ""))
                    cdm_type = LayerType.INNER_COPPER
                    cdm_index = idx
                except ValueError:
                    print(f"Warning: Could not parse index for inner layer: {parts[1]}")
                    cdm_type = LayerType.DOCUMENTATION  # Fallback
            else:  # Fallback for unknown layers
                print(
                    f"Warning: Unknown EasyEDA layer name '{parts[1]}' (id: {ee_id}). Mapping to DOCUMENTATION."
                )
                cdm_type = LayerType.DOCUMENTATION

            if cdm_type == LayerType.MECHANICAL:
                mechanical_layer_count += 1
                cdm_index = mechanical_layer_count

            if cdm_type:
                self.layer_map[ee_id] = LayerRef(type=cdm_type, index=cdm_index)
                if cdm_type.value.endswith("_mask"):
                    self.mask_layer_properties[ee_id] = (cdm_type, expansion)
            elif (
                ee_id.lower() == "hole"
            ):  # Special "Hole" definition, not really a layer for drawing on.
                pass  # No direct LayerRef, but might store its properties if needed elsewhere.

    def _parse_pad(
        self, parts: List[str], offset_x: float, offset_y: float
    ) -> Optional[Pad]:
        # PAD~shape~centerX~centerY~width~height~layerId~net~number~holeRadius~points~rotation~id~holeLength~holePoint~isPlated
        # indices:0    1      2       3      4      5       6        7    8       9           10     11      12  13         14         15
        # Note: `points` for polygon pads, `holeLength` for slotted holes.
        # `isPlated` is often empty or "Y"
        try:
            ee_shape_str = parts[1]
            center_x = float(parts[2]) * self.unit_scale - offset_x
            center_y = float(parts[3]) * self.unit_scale - offset_y
            width = float(parts[4]) * self.unit_scale
            height = float(parts[5]) * self.unit_scale
            layer_id_str = parts[6]
            # net_name = parts[7] # Not used in CDM pad directly
            pad_number = parts[8]

            hole_radius_str = parts[9]
            # points_str = parts[10] for polygon pads
            rotation_str = parts[11]
            # id_str = parts[12]
            hole_length_str = parts[13]  # For slotted holes
            # hole_point_str = parts[14]
            is_plated_str = (
                parts[15] if len(parts) > 15 else "Y"
            )  # Default to plated if THT

            pad_layer = self.layer_map.get(layer_id_str)
            if not pad_layer:
                print(
                    f"Warning: Unknown layer ID '{layer_id_str}' for PAD {pad_number}. Skipping."
                )
                return None

            pad_type = PadType.SMD
            drill_diameter: Optional[float] = None
            drill_slot_length: Optional[float] = None
            drill_shape: Optional[DrillShape] = DrillShape.ROUND
            plated: bool = True  # Default for THT style pads

            if hole_radius_str and float(hole_radius_str) > 0:
                pad_type = PadType.THROUGH_HOLE
                drill_diameter = float(hole_radius_str) * 2 * self.unit_scale
                plated = not (
                    is_plated_str.upper() == "N"
                    or is_plated_str == "false"
                    or is_plated_str == "0"
                )

                if hole_length_str and float(hole_length_str) > 0:
                    drill_slot_length = float(hole_length_str) * self.unit_scale
                    drill_shape = DrillShape.OBLONG
                else:
                    drill_shape = DrillShape.ROUND
            elif (
                pad_layer.type == LayerType.MULTI_LAYER
            ):  # If explicitly multi-layer but no drill, might be an issue
                pad_type = PadType.CONNECT  # Or could be an error, or an implicit via

            start_layer, end_layer = None, None
            if pad_type in [PadType.THROUGH_HOLE, PadType.VIA]:
                # Assume THT/Via spans all copper layers unless specified otherwise.
                # A more sophisticated system would know the board stackup.
                # For now, let's default to Top <-> Bottom for simplicity if it's on an outer layer.
                if (
                    pad_layer.type == LayerType.TOP_COPPER
                    or pad_layer.type == LayerType.MULTI_LAYER
                ):
                    start_layer = LayerRef(type=LayerType.TOP_COPPER)
                    end_layer = LayerRef(
                        type=LayerType.BOTTOM_COPPER
                    )  # Default assumption
                elif pad_layer.type == LayerType.BOTTOM_COPPER:
                    start_layer = LayerRef(type=LayerType.BOTTOM_COPPER)
                    end_layer = LayerRef(
                        type=LayerType.TOP_COPPER
                    )  # Default assumption

            cdm_shape: Optional[PadShape] = None
            if ee_shape_str == "RECT":
                cdm_shape = PadShape.ROUNDRECT
            elif ee_shape_str == "OVAL":
                cdm_shape = PadShape.OVAL
            elif ee_shape_str == "ELLIPSE":  # Map to CIRCLE if w=h, else OVAL
                cdm_shape = PadShape.CIRCLE if width == height else PadShape.OVAL
            elif ee_shape_str == "POLYGON":
                cdm_shape = PadShape.POLYGON
            else:
                print(
                    f"Warning: Unknown EasyEDA pad shape '{ee_shape_str}'. Defaulting to RECTANGLE."
                )
                cdm_shape = PadShape.ROUNDRECT

            # Mask margins - need to fetch from layer properties
            solder_mask_margin, paste_mask_margin = None, None
            # This is a simplification. Real systems might have per-pad overrides or complex rules.
            for _, (mask_type, expansion) in self.mask_layer_properties.items():
                if expansion is not None:
                    if mask_type in [
                        LayerType.TOP_SOLDER_MASK,
                        LayerType.BOTTOM_SOLDER_MASK,
                    ]:
                        solder_mask_margin = expansion * self.unit_scale
                    elif mask_type in [
                        LayerType.TOP_PASTE_MASK,
                        LayerType.BOTTOM_PASTE_MASK,
                    ]:
                        paste_mask_margin = expansion * self.unit_scale

            return Pad(
                number=pad_number,
                uuid=uuid4(),
                pad_type=pad_type,
                shape=cdm_shape,
                position=Point(x=center_x, y=center_y),
                width=width,
                height=height
                if cdm_shape != PadShape.CIRCLE
                else width,  # Height same as width for circle
                rotation=float(rotation_str) if rotation_str else 0.0,
                layer=pad_layer,
                drill_shape=drill_shape if drill_diameter else None,
                drill_diameter=drill_diameter,
                drill_slot_length=drill_slot_length,
                plated=plated if drill_diameter else None,
                start_layer=start_layer,
                end_layer=end_layer,
                solder_mask_margin=solder_mask_margin,
                paste_mask_margin=paste_mask_margin,
                vertices=parse_svg_path_to_points(
                    parts[10], offset_x, offset_y, self.unit_scale
                )
                if cdm_shape == PadShape.POLYGON and parts[10]
                else None,
            )
        except Exception as e:
            print(f"Error parsing PAD string '{'~'.join(parts)}': {e}")
            return None

    def _parse_track(
        self, parts: List[str], offset_x: float, offset_y: float
    ) -> Optional[Union[Line, Polyline]]:
        # TRACK~strokeWidth~layerId~net~points~id~isLocked
        # points: "X1 Y1 X2 Y2 X3 Y3..."
        try:
            stroke_width = float(parts[1]) * self.unit_scale
            layer_id_str = parts[2]
            # net = parts[3]
            points_str = parts[4]

            track_layer = self.layer_map.get(layer_id_str)
            if not track_layer:
                print(
                    f"Warning: Unknown layer ID '{layer_id_str}' for TRACK. Skipping."
                )
                return None

            raw_coords = [float(c) for c in points_str.split(" ") if c]
            if len(raw_coords) < 4 or len(raw_coords) % 2 != 0:
                print(f"Warning: Invalid points for TRACK '{points_str}'. Skipping.")
                return None

            cdm_points: List[Point] = []
            for i in range(0, len(raw_coords), 2):
                cdm_points.append(
                    Point(
                        x=raw_coords[i] * self.unit_scale - offset_x,
                        y=raw_coords[i + 1] * self.unit_scale - offset_y,
                    )
                )

            if len(cdm_points) == 2:
                return Line(
                    start=cdm_points[0],
                    end=cdm_points[1],
                    width=stroke_width,
                    layer=track_layer,
                )
            else:
                return Polyline(
                    points=cdm_points, width=stroke_width, layer=track_layer
                )
        except Exception as e:
            print(f"Error parsing TRACK string '{'~'.join(parts)}': {e}")
            return None

    def _parse_circle_primitive(
        self, parts: List[str], offset_x: float, offset_y: float
    ) -> Optional[Circle]:
        # CIRCLE~cx~cy~radius~strokeWidth~layerId~id~isLocked~~ (last empty field in example)
        try:
            cx = float(parts[1]) * self.unit_scale - offset_x
            cy = float(parts[2]) * self.unit_scale - offset_y
            radius = float(parts[3]) * self.unit_scale
            stroke_width = float(parts[4]) * self.unit_scale
            layer_id_str = parts[5]

            circle_layer = self.layer_map.get(layer_id_str)
            if not circle_layer:
                print(
                    f"Warning: Unknown layer ID '{layer_id_str}' for CIRCLE. Skipping."
                )
                return None

            return Circle(
                center=Point(x=cx, y=cy),
                radius=radius,
                stroke_width=stroke_width,
                filled=False,  # EasyEDA circles are typically outlines
                layer=circle_layer,
            )
        except Exception as e:
            print(f"Error parsing CIRCLE string '{'~'.join(parts)}': {e}")
            return None

    def _parse_arc_primitive(
        self, parts: List[str], offset_x: float, offset_y: float
    ) -> Optional[Arc]:
        # ARC~strokeWidth~layerId~net~path~helperDots~id~isLocked
        # path is an SVG path string, e.g., "M X Y A RX RY XROT LARGEARC SWEEP X Y"
        try:
            stroke_width = float(parts[1]) * self.unit_scale
            layer_id_str = parts[2]
            # net = parts[3]
            path_str = parts[4]

            arc_layer = self.layer_map.get(layer_id_str)
            if not arc_layer:
                print(f"Warning: Unknown layer ID '{layer_id_str}' for ARC. Skipping.")
                return None

            # Extremely simplified SVG 'A' command parsing
            # Example: M 395 300 A 5 5 0 0 1 400 295
            match = re.match(
                r"M\s*([\d\.]+)\s*([\d\.]+)\s*A\s*([\d\.]+)\s*([\d\.]+)\s*([\d\.]+)\s*([01])\s*([01])\s*([\d\.]+)\s*([\d\.]+)",
                path_str,
                re.IGNORECASE,
            )
            if match:
                m_x, m_y, a_rx, a_ry, a_xrot, a_large_arc_f, a_sweep_f, a_x, a_y = map(
                    float, match.groups()
                )

                # Call the complex conversion function (currently a placeholder)
                center, radius_x, start_angle, sweep_angle = (
                    convert_svg_arc_to_center_params(
                        m_x,
                        m_y,
                        a_x,
                        a_y,
                        bool(int(a_large_arc_f)),
                        bool(int(a_sweep_f)),
                        a_rx,
                        a_ry,
                        a_xrot,
                        self.unit_scale,  # Pass unit_scale to be applied inside
                    )
                )

                # Note: convert_svg_arc_to_center_params should apply unit_scale to its inputs
                # or its outputs. If it applies to inputs, then pass raw values.
                # Here, it's assumed it works with scaled values or applies scaling.
                # The current placeholder applies scaling to dummy values.
                # For radius_x, it should be radius_x * self.unit_scale if a_rx was raw.

                return Arc(
                    center=center,  # Already scaled by convert_svg_arc_to_center_params
                    radius=radius_x,  # Assuming radius_x and radius_y are same for CDM Arc, take one
                    start_angle=start_angle,  # In degrees
                    end_angle=start_angle + sweep_angle,  # CDM expects end_angle
                    width=stroke_width,  # Already scaled
                    layer=arc_layer,
                )
            else:
                print(
                    f"Warning: Could not parse SVG ARC path string '{path_str}'. Skipping."
                )
                return None

        except Exception as e:
            print(f"Error parsing ARC string '{'~'.join(parts)}': {e}")
            return None

    def _parse_solidregion(
        self, parts: List[str], offset_x: float, offset_y: float
    ) -> Optional[Polygon]:
        # SOLIDREGION~layerId~~Path~Type~RepID~~~~locked
        # Example: SOLIDREGION~100~~M390...Z~solid~rep3~~~~0
        # Indices:    0          1   2  3    4    5      6 7 8 9
        try:
            layer_id_str = parts[1]
            path_str = parts[3]
            # type_str = parts[4] # e.g., "solid"

            poly_layer = self.layer_map.get(layer_id_str)
            if not poly_layer:
                print(
                    f"Warning: Unknown layer ID '{layer_id_str}' for SOLIDREGION. Skipping."
                )
                return None

            vertices = parse_svg_path_to_points(
                path_str, offset_x, offset_y, self.unit_scale
            )
            if not vertices or len(vertices) < 3:
                print(
                    f"Warning: Not enough vertices for SOLIDREGION '{path_str}'. Skipping."
                )
                return None

            return Polygon(
                vertices=vertices,
                stroke_width=0,  # Solid regions are filled, stroke usually not relevant or minimal
                filled=True,
                layer=poly_layer,
            )
        except Exception as e:
            print(f"Error parsing SOLIDREGION string '{'~'.join(parts)}': {e}")
            return None

    def _parse_text_primitive(
        self, parts: List[str], offset_x: float, offset_y: float
    ) -> Optional[Text]:
        # TEXT~type~centerX~centerY~strokeWidth~rotation~mirror~layerId~net~fontSize~display~text~path~id~locked
        # type: N (name), P (prefix/value)
        # mirror: 0 or 1
        # display: "FILTER" "ALWAYS" etc. or empty string for visible
        try:
            # text_type_indicator = parts[1] # e.g. "REF", "VAL" if available
            center_x = float(parts[2]) * self.unit_scale - offset_x
            center_y = float(parts[3]) * self.unit_scale - offset_y
            stroke_width = float(parts[4]) * self.unit_scale
            rotation = float(parts[5]) if parts[5] else 0.0
            mirrored = parts[6] == "1"
            layer_id_str = parts[7]
            # net = parts[8]
            font_height = (
                float(parts[9]) * self.unit_scale
            )  # EasyEDA font_size is height
            # display_flag = parts[10]
            text_content = parts[11]

            text_layer = self.layer_map.get(layer_id_str)
            if not text_layer:
                print(
                    f"Warning: Unknown layer ID '{layer_id_str}' for TEXT '{text_content}'. Skipping."
                )
                return None

            return Text(
                text=text_content,
                position=Point(x=center_x, y=center_y),
                font_height=font_height,
                stroke_width=stroke_width,
                rotation=rotation,
                mirrored=mirrored,
                visible=True,  # TODO: Parse display_flag for visibility
                layer=text_layer,
                horizontal_align=TextAlignHorizontal.CENTER,  # EasyEDA text anchor often center
                vertical_align=TextAlignVertical.MIDDLE,  # EasyEDA text anchor often middle
            )
        except Exception as e:
            print(f"Error parsing TEXT string '{'~'.join(parts)}': {e}")
            return None

    def _parse_hole_primitive(
        self, parts: List[str], offset_x: float, offset_y: float
    ) -> Optional[Drill]:
        # HOLE~X~Y~Radius~TRACKID~NET~ID~LOCKED
        # Example from parameters_easyeda.py: EeFootprintHole
        # center_x, center_y, radius, id, is_locked
        try:
            center_x = float(parts[1]) * self.unit_scale - offset_x
            center_y = float(parts[2]) * self.unit_scale - offset_y
            radius = float(parts[3]) * self.unit_scale

            return Drill(
                position=Point(x=center_x, y=center_y),
                shape=DrillShape.ROUND,
                diameter=radius * 2,
                plated=False,  # Standalone HOLE objects in EasyEDA are typically NPTH
                layer=LayerRef(type=LayerType.MULTI_LAYER),  # Holes span layers
            )
        except Exception as e:
            print(f"Error parsing HOLE string '{'~'.join(parts)}': {e}")
            return None

    def _parse_rect_primitive(
        self, parts: List[str], offset_x: float, offset_y: float
    ) -> Optional[Rectangle]:
        # RECT~X~Y~Width~Height~strokeWidth~ID~LayerID~Locked
        # (from parameters_easyeda.py EeFootprintRectangle)
        try:
            x = float(parts[1]) * self.unit_scale - offset_x  # Top-left X
            y = float(parts[2]) * self.unit_scale - offset_y  # Top-left Y
            width = float(parts[3]) * self.unit_scale
            height = float(parts[4]) * self.unit_scale
            stroke_width = float(parts[5]) * self.unit_scale
            layer_id_str = parts[7]

            rect_layer = self.layer_map.get(layer_id_str)
            if not rect_layer:
                print(f"Warning: Unknown layer ID '{layer_id_str}' for RECT. Skipping.")
                return None

            return Rectangle(
                position=Point(
                    x=x + width / 2, y=y + height / 2
                ),  # CDM uses center point
                width=width,
                height=height,
                stroke_width=stroke_width,
                filled=False,  # EasyEDA rects are typically outlines
                layer=rect_layer,
            )
        except Exception as e:
            print(f"Error parsing RECT string '{'~'.join(parts)}': {e}")
            return None

    def _parse_svgnode(self, parts: List[str]) -> Optional[Model3D]:
        svg_node = json.loads(parts[1])
        attrs_3d = svg_node.get("attrs", {})
        if attrs_3d.get("uuid"):
            uuid_3d = UUID(attrs_3d["uuid"])
            # attrs': {'c_etype': 'outline3D',
            #    'c_height': '11.0236',
            #    'c_origin': '3999.5011,2998',
            #    'c_rotation': '0,0,0',
            #    'c_width': '11.4173',
            #    'id': 'g1_outline',
            #    'layerid': '19',
            #    'title': 'SOT-25-5_L2.9-W1.6-P0.95-LS2.8-BL',
            #    'transform': 'scale(1) translate(0, 0)',
            #    'uuid': '6d166d1d6c064b99aa79465714e989c1',
            # TODO handle title, rotation, and transform
            model = Model3D(uuid=uuid_3d)
            return model
        return None

    def parse_easyeda_json(self, easyeda_data: Dict[str, Any]) -> Optional[Footprint]:
        if "packageDetail" not in easyeda_data:
            print("Error: 'packageDetail' not found in EasyEDA data.")
            return None

        package_detail = easyeda_data["packageDetail"]
        if "dataStr" not in package_detail or not package_detail["dataStr"]:
            print("Error: 'dataStr' for footprint not found or is empty.")
            # This can happen if the component only has a symbol but no footprint
            return None  # Or return an empty Footprint object if that's desired

        data_str = package_detail["dataStr"]
        head = data_str.get("head", {})
        height = data_str.get("BBox", {}).get("height", 0) * self.unit_scale
        width = data_str.get("BBox", {}).get("width", 0) * self.unit_scale

        self._parse_layer_definitions(data_str.get("layers", []))

        # --- Metadata ---
        footprint_name = (
            head.get("c_para", {}).get("package")
            or head.get("name")
            or package_detail.get("title", "UnknownFootprint")
        )
        fp_uuid_str = head.get("uuid")
        fp_uuid = UUID(fp_uuid_str) if fp_uuid_str else None

        author = head.get("c_para", {}).get("Contributor")

        created_at: Optional[datetime] = None
        utime = head.get("utime")
        if utime:
            try:
                created_at = datetime.fromtimestamp(int(utime))
            except ValueError:
                pass

        generated_by = f"EasyEDA Editor {head.get('editorVersion', 'unknown')}"

        keywords = easyeda_data.get("tags", [])

        custom_attrs = {}
        c_para = head.get("c_para", {})
        if "Manufacturer" in c_para:
            custom_attrs["Manufacturer"] = c_para["Manufacturer"]
        if "Manufacturer Part" in c_para:
            custom_attrs["Manufacturer Part"] = c_para["Manufacturer Part"]
        if "link" in c_para:
            custom_attrs["Datasheet Link"] = c_para["link"]
        if "Supplier Part" in c_para:
            custom_attrs["LCSC Part"] = c_para["Supplier Part"]

        offset_x_easyeda_units = head.get("x", 0.0)  # Keep original EasyEDA units
        offset_y_easyeda_units = head.get("y", 0.0)  # Keep original EasyEDA units
        offset_x = (
            offset_x_easyeda_units * self.unit_scale
        )  # Convert to mm for pad positioning
        offset_y = (
            offset_y_easyeda_units * self.unit_scale
        )  # Convert to mm for pad positioning
        print(f"Offset: {offset_x}, {offset_y}")

        fp = Footprint(
            name=footprint_name,
            uuid=fp_uuid,
            author=author,
            created_at=created_at,
            generated_by=generated_by,
            keywords=keywords,
            description=easyeda_data.get("description"),
            custom_attributes=custom_attrs,
            pads=[],
            graphics=[],
            height=height,
            width=width,
            source_offset_x=offset_x_easyeda_units,  # Store original source units
            source_offset_y=offset_y_easyeda_units,  # Store original source units
        )

        # --- Shapes ---
        for shape_str in data_str.get("shape", []):
            parts = shape_str.split("~")
            shape_type = parts[0]

            element: Optional[Union[Pad, GraphicElement]] = None

            if shape_type == "PAD":
                element = self._parse_pad(parts, offset_x, offset_y)
            elif shape_type == "TRACK":
                element = self._parse_track(parts, offset_x, offset_y)
            elif shape_type == "CIRCLE":
                element = self._parse_circle_primitive(parts, offset_x, offset_y)
            elif shape_type == "ARC":
                element = self._parse_arc_primitive(
                    parts, offset_x, offset_y
                )  # Needs robust SVG arc parsing
            elif shape_type == "SOLIDREGION":
                element = self._parse_solidregion(parts, offset_x, offset_y)
            elif shape_type == "TEXT":
                element = self._parse_text_primitive(parts, offset_x, offset_y)
            elif shape_type == "HOLE":  # From prior art, implies standalone NPTH
                element = self._parse_hole_primitive(parts, offset_x, offset_y)
            elif shape_type == "RECT":  # From prior art, non-pad rectangle
                element = self._parse_rect_primitive(parts, offset_x, offset_y)
            elif shape_type == "SVGNODE":
                fp.model_3d = self._parse_svgnode(parts)
            # elif shape_type == "VIA": # VIA specific parsing if needed
            #     element = self._parse_via_primitive(parts, offset_x, offset_y)
            else:
                print(f"Notice: Unhandled EasyEDA shape type: {shape_type}")
                raise Exception(f"Unhandled shape type: {type(element)}")

            if element:
                if isinstance(element, Pad):
                    fp.pads.append(element)
                elif isinstance(element, GraphicElement):  # Check against the Union
                    fp.graphics.append(element)
                else:
                    raise Exception(f"Unhandled element type: {type(element)}")

        return fp

    def calculate_footprint_alignment(
        self, footprint: Footprint, svg_path: str, png_path: str
    ):
        """
        Calculate alignment for a footprint using data stored in the footprint object.

        Args:
            footprint: The parsed Footprint object (with source_offset_x/y)
            svg_path: Path to SVG file (for viewBox)
            png_path: Path to PNG file (for pixel dimensions)

        Returns:
            FootprintAlignment object
        """
        from models.footprint import AlignmentCalculator
        from svg_utils import (
            parse_svg_viewbox,
            get_png_dimensions,
            create_coordinate_mapper,
        )

        if footprint.source_offset_x is None or footprint.source_offset_y is None:
            raise ValueError(
                "Footprint missing source offset data - was it parsed correctly?"
            )

        # Get SVG and PNG information using shared utilities
        svg_info = parse_svg_viewbox(svg_path)
        png_info = get_png_dimensions(png_path)

        # Create coordinate mapper using shared utility
        coordinate_mapper = create_coordinate_mapper(
            svg_info=svg_info,
            png_info=png_info,
            source_offset_x=footprint.source_offset_x,
            source_offset_y=footprint.source_offset_y,
            unit_scale=self.unit_scale,
        )

        # Use the generic alignment calculator
        calculator = AlignmentCalculator()
        alignment = calculator.calculate_alignment(
            footprint=footprint,
            coordinate_mapper=coordinate_mapper,
        )

        return alignment
