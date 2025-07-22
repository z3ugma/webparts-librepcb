# Global imports
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, NamedTuple, Optional, Tuple, Union
from uuid import UUID, uuid4

from librepcb_parts_generator.entities.common import (
    Align,
    Angle,
    Author,
    Category,
    Circle,
    Created,
    Deprecated,
    Description,
    Diameter,
    Fill,
    GeneratedBy,
    GrabArea,
    Height,
    Keywords,
    Layer,
    Name,
    Polygon,
    Position,
    Position3D,
    Rotation,
    Rotation3D,
    Value,
    Version,
    Vertex,
    Width,
)
from librepcb_parts_generator.entities.package import (
    AssemblyType,
    AutoRotate,
    ComponentSide,
    CopperClearance,
    DrillDiameter,
    Footprint,
    Footprint3DModel,
    FootprintPad,
    Hole,
    Layer,
    LetterSpacing,
    LineSpacing,
    Mirror,
    Package,
    Package3DModel,
    PackagePad,
    PackagePadUuid,
    PadFunction,
    PadHole,
    Position,
    Shape,
    ShapeRadius,
    Size,
    SolderPasteConfig,
    StopMaskConfig,
    StrokeText,
    StrokeWidth,
)

from models.library_part import LibraryPart
from constants import DEFAULT_VERSION

logger = logging.getLogger(__name__)


# Define Number for type hinting
Number = Union[int, float]


class Pad(NamedTuple):
    footprint_pad: FootprintPad
    package_pad: PackagePad


class Model3DWithOrigin(NamedTuple):
    model: Footprint3DModel
    position_3d: Position3D
    rotation_3d: Rotation3D


# Convert EasyEDA's internal geometric units (10 mil per unit) into millimeters.
# 1 unit = 10 mil → 0.254 mm.
# The canvas 'unit' field is only for editor display (grid/snap), not for shape data.
UNIT_SCALE = 0.254


# # Placeholder for SVG Arc to Center-Position conversion (Complex)
# def convert_svg_arc_to_center_params(
#     x1: float,
#     y1: float,
#     x2: float,
#     y2: float,
#     fa: bool,
#     fs: bool,
#     rx: float,
#     ry: float,
#     phi_degrees: float,
#     offset_x: float,
#     offset_y: float,
#     UNIT_SCALE: float,
# ) -> Tuple[Position, float, float, float]:  # center, radius_x, start_angle, sweep_angle
#     # This is a non-trivial conversion.
#     # See: https://www.w3.org/TR/SVG/implnote.html#ArcImplementationNotes
#     # For now, returning dummy values.
#     # A proper implementation would involve matrix math and trigonometry.
#     print(
#         f"Warning: SVG Arc parsing is complex and not fully implemented. Shape: A {rx} {ry} {phi_degrees} {1 if fa else 0} {1 if fs else 0} {x2} {y2}"
#     )
#     # Using scaled coordinates for dummy values
#     scaled_x1, scaled_y1 = x1 * UNIT_SCALE, y1 * UNIT_SCALE
#     scaled_x2, scaled_y2 = x2 * UNIT_SCALE, y2 * UNIT_SCALE
#     center_x = (scaled_x1 + scaled_x2) / 2
#     center_y = (scaled_y1 + scaled_y2) / 2
#     radius = ((scaled_x2 - scaled_x1) ** 2 + (scaled_y2 - scaled_y1) ** 2) ** 0.5 / 2
#     return (
#         Position(x=center_x, y=center_y),
#         radius,
#         0.0,
#         180.0,
#     )  # Dummy start_angle, sweep_angle


class EasyEDAFootprintParser:
    def __init__(self):
        self.layer_map: Dict[str, Layer] = {}
        self.unfilled_layers: List[Layer] = []
        self.side_map: Dict[str, ComponentSide] = {}
        self.offset_x = 0.0
        self.offset_y = 0.0

    def xpos(self, cx: Number) -> float:
        return float(cx) * UNIT_SCALE - self.offset_x

    def ypos(self, cy: Number) -> float:
        return (float(cy) * UNIT_SCALE - self.offset_y) * -1

    # --- SVG Path Parsing (Simplified for M, L, H, V, Z) ---
    # For full SVG arc (A) to center-point conversion, a more robust library or implementation is needed.
    # For now, we'll focus on simpler paths and leave Arc parsing as a TODO if complex.

    def parse_svg_path_to_points(self, path_str: str) -> List[Position]:
        points: List[Position] = []

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
        command_groups = re.findall(
            r"([MLHVZ])([^MLHVZ]*)", path_str, flags=re.IGNORECASE
        )

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

                    scaled_x = self.xpos(current_x)
                    scaled_y = self.ypos(current_y)
                    points.append(Position(x=scaled_x, y=scaled_y))
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
                        Position(
                            x=self.xpos(current_x),
                            y=self.ypos(current_y),
                        )
                    )

            elif command == "H":  # Horizontal lineto
                for val in raw_coords:
                    if is_relative:
                        current_x += val
                    else:
                        current_x = val
                    points.append(
                        Position(
                            x=self.xpos(current_x),
                            y=self.ypos(current_y),
                        )
                    )

            elif command == "V":  # Vertical lineto
                for val in raw_coords:
                    if is_relative:
                        current_y += val
                    else:
                        current_y = val
                    points.append(
                        Position(
                            x=self.xpos(current_x),
                            y=self.ypos(current_y),
                        )
                    )

            elif command == "Z":  # ClosePath
                if points and (points[-1].x != start_x or points[-1].y != start_y):
                    points.append(Position(x=start_x, y=start_y))
                # After Z, the path is closed. A new M should follow if path continues.
                # For simple polygons, this is usually the end.
                current_x, current_y = (
                    start_x / UNIT_SCALE,
                    start_y / UNIT_SCALE,
                )  # Reset current point to start

        return points

    def _parse_layer_definitions(self, layer_strings: List[str]):
        """
        Parses EasyEDA layer definitions and populates self.layer_map and self.mask_expansions.
        Example: "1~TopLayer~#FF0000~true~false~true~"
        """
        self.layer_map = {}
        self.side_map = {}
        self.mask_layer_properties = {}
        self.easyeda_layer_id_to_name = {}

        # Basic mapping from EasyEDA layer names/IDs to CDM LayerType
        # This needs to be comprehensive based on common EasyEDA usage
        # From https://github.com/dillonHe/EasyEDA-Documents/blob/master/Open-File-Format/PCB.md

        layer_names_map = {
            # EasyEDA: #LibrePCB
            "boardoutline": Layer("brd_outlines"),
            "bottomlayer": Layer("bot_cu"),
            "bottompastemasklayer": Layer("bot_stop_mask"),
            "bottompasterlayer": Layer("bot_solder_paste"),
            "bottomsilklayer": Layer("bot_legend"),
            "bottomsolderlayer": Layer("bot_solder_paste"),
            "bottomsoldermasklayer": Layer("bot_documentation"),
            "componentmarkinglayer": Layer("brd_documentation"),
            "componentpolaritylayer": Layer("brd_documentation"),
            "componentshapelayer": Layer("top_package_outlines"),
            "document": Layer("brd_documentation"),
            "hole": Layer("brd_documentation"),
            "drcerror": Layer("brd_documentation"),
            "ratlines": Layer("brd_documentation"),
            "mechanical": Layer("brd_documentation"),
            "3dmodel": Layer("brd_documentation"),
            "leadshapelayer": Layer("brd_documentation"),
            "multi-layer": Layer("top_cu"),
            "toplayer": Layer("top_cu"),
            "toppastemasklayer": Layer("top_stop_mask"),
            "toppasterlayer": Layer("top_solder_paste"),
            "topsilklayer": Layer("top_legend"),
            "topsolderlayer": Layer("top_solder_paste"),
            "topsoldermasklayer": Layer("top_documentation"),
            "topassembly": Layer("top_documentation"),
            "bottomassembly": Layer("bot_documentation"),
            "all": Layer("top_documentation"),
            # "TopLayer": Layer("top_cu"),
            # "Multi-Layer": Layer("top_cu"),
            # "BottomLayer": Layer("bot_cu"),
            # "TopSilkLayer": Layer("top_legend"),
            # "BottomSilkLayer": Layer("bot_legend"),
            # "TopPasterLayer": Layer("top_solder_paste"),
            # "TopPasteMaskLayer": Layer("top_stop_mask"),
            # "BottomPasterLayer": Layer("bot_solder_paste"),
            # "BottomPasteMaskLayer": Layer("bot_stop_mask"),
            # "TopSolderLayer": Layer("top_solder_paste"),
            # "BottomSolderLayer": Layer("bot_solder_paste"),
            # "TopSolderMaskLayer": Layer("top_documentation"),
            # "BottomSolderMaskLayer": Layer("bot_documentation"),
            # "BoardOutline": Layer("brd_outlines"),
            # "Document": Layer("brd_documentation"),
            # "LeadShapeLayer": Layer("brd_documentation"),
            # "ComponentMarkingLayer": Layer("brd_documentation"),
            # "ComponentShapeLayer": Layer("top_package_outlines"),
            # "ComponentPolarityLayer": Layer("brd_documentation"),
            # "topLayer": Layer(""),
            # "bottomLayer": Layer(""),
            # "topSilkLayer": Layer(""),
            # "bottomSilkLayer": Layer(""),
            # "topPasterLayer": Layer(""),
            # "bottomPasterLayer": Layer(""),
            # "topSolderLayer": Layer(""),
            # "bottomSolderLayer": Layer(""),
            # "all": Layer(""),
            # "document": Layer("")
            # Unknown layer: Ratlines
            # Unknown layer: BoardOutLine
            # Unknown layer: Multi-Layer
            # Unknown layer: TopAssembly
            # Unknown layer: BottomAssembly
            # Unknown layer: Mechanical
            # Unknown layer: 3DModel
            # Unknown layer: ComponentShapeLayer
            # Unknown layer: LeadShapeLayer
            # Unknown layer: ComponentMarkingLayer
            # Unknown layer: Hole
            # Unknown layer: DRCError
            #
            # All LibrePCB Layers
            # "bot_courtyard", tr("Bottom Courtyard"),
            # "bot_documentation", tr("Bottom Documentation"),
            # "bot_finish", tr("Bottom Finish"),
            # "bot_glue", tr("Bottom Glue"), Theme::Color::sBoardGlueBot,
            # "bot_hidden_grab_areas", tr("Bottom Hidden Grab Areas"),
            # "bot_legend", tr("Bottom Legend"),
            # "bot_names", tr("Bottom Names"),
            # "bot_package_outlines", tr("Bottom Package Outlines"),
            # "bot_solder_paste", tr("Bottom Solder Paste"),
            # "bot_stop_mask", tr("Bottom Stop Mask"),
            # "bot_values", tr("Bottom Values"),
            # "brd_alignment", tr("Alignment"),
            # "brd_comments", tr("Comments"),
            # "brd_cutouts", tr("Board Cutouts"),
            # "brd_documentation", tr("Documentation"),
            # "brd_frames", tr("Sheet Frames"),
            # "brd_guide", tr("Guide"), Theme::Color::sBoardGuide,
            # "brd_measures", tr("Measures"),
            # "brd_outlines", tr("Board Outlines"),
            # "brd_plated_cutouts", tr("Plated Board Cutouts"),
            # "sch_comments", tr("Comments"),
            # "sch_documentation", tr("Documentation"),
            # "sch_frames", tr("Sheet Frames"),
            # "sch_guide", tr("Guide"), Theme::Color::sSchematicGuide,
            # "sym_hidden_grab_areas", tr("Hidden Grab Areas"),
            # "sym_names", tr("Names"), Theme::Color::sSchematicNames,
            # "sym_outlines", tr("Outlines"),
            # "sym_pin_names", tr("Pin Names"),
            # "sym_values", tr("Values"), Theme::Color::sSchematicValues,
            # "top_courtyard", tr("Top Courtyard"),
            # "top_cu", tr("Top Copper"), Theme::Color::sBoardCopperTop,
            # "top_documentation", tr("Top Documentation"),
            # "top_finish", tr("Top Finish"),
            # "top_glue", tr("Top Glue"), Theme::Color::sBoardGlueTop,
            # "top_hidden_grab_areas", tr("Top Hidden Grab Areas"),
            # "top_legend", tr("Top Legend"),
            # "top_names", tr("Top Names"), Theme::Color::sBoardNamesTop,
            # "top_package_outlines", tr("Top Package Outlines"),
            # "top_solder_paste", tr("Top Solder Paste"),
            # "top_stop_mask", tr("Top Stop Mask"),
            # "top_values", tr("Top Values"),
        }
        for i in range(1, 33):
            layer_names_map[f"inner{i}"] = (Layer("in{i}_cu"),)

        side_names_map = {
            # EasyEDA: #LibrePCB
            "toplayer": ComponentSide.TOP,
            "bottomlayer": ComponentSide.BOTTOM,
            "multi-layer": ComponentSide.TOP,
        }

        self.unfilled_layers = [k.layer for k in [Layer("top_package_outlines")]]

        for layer_str in layer_strings:
            parts = layer_str.split("~")
            ee_id = parts[0]
            ee_name = parts[1].lower()

            lp_layer = layer_names_map.get(ee_name)
            if lp_layer:
                self.layer_map[ee_id] = lp_layer
            else:
                logger.error(f"Unknown layer: {ee_id} {ee_name}")

            lp_side = side_names_map.get(ee_name)
            if lp_side:
                self.side_map[ee_id] = lp_side

    def _parse_pad(self, parts: List[str]) -> Optional[Pad]:
        #         PAD~shape~centerX~centerY~width~height~layerId~net~number~holeRadius~points~rotation~id~holeLength~holePosition~isPlated
        # indices:0   1     2       3      4      5      6       7   8      9          10     11       12 13         14           15
        # Note: `points` for polygon pads, `holeLength` for slotted holes.
        # `isPlated` is often empty or "Y"
        try:
            ee_shape_str = parts[1]
            center_x = self.xpos(parts[2])
            center_y = self.ypos(parts[3])
            width = float(parts[4]) * UNIT_SCALE
            height = float(parts[5]) * UNIT_SCALE

            layer_id_str = parts[6]

            # net_name = parts[7] # Not used in CDM pad directly
            pad_number = parts[8]

            hole_radius_str = parts[9]
            # points_str = parts[10] for polygon pads
            rotation_str = parts[11]
            # id_str = parts[12]
            hole_length_str = parts[13]  # For slotted holes
            hole_point_str = parts[14]
            is_plated_str = (
                parts[15] if len(parts) > 15 else "Y"
            )  # Default to plated if THT

            side = self.side_map.get(layer_id_str)
            if not side:
                raise Exception(f"No ComponentSide found for layer ID {layer_id_str}")

            # drill_diameter: Optional[float] = None
            # drill_slot_length: Optional[float] = None
            # drill_shape: Optional[DrillShape] = DrillShape.ROUND
            # plated: bool = True  # Default for THT style pads

            holes: List[PadHole] = []

            if float(hole_radius_str) > 0 or hole_point_str:
                logger.info(f"This pad has holes: {pad_number}")
                drill_diameter = float(hole_radius_str) * 2 * UNIT_SCALE
                plated = not (
                    is_plated_str.upper() == "N"
                    or is_plated_str == "false"
                    or is_plated_str == "0"
                )

                if hole_length_str and float(hole_length_str) > 0:
                    drill_slot_length = float(hole_length_str) * UNIT_SCALE

                vertices: List[Position] = []
                raw_coords = [float(c) for c in hole_point_str.split(" ") if c]
                if raw_coords:  # This is a list of coordinates, implying a slotted hole
                    for i in range(0, len(raw_coords), 2):
                        vertices.append(
                            Vertex(
                                Position(
                                    x=self.xpos(raw_coords[i]) - center_x,
                                    y=self.ypos(raw_coords[i + 1]) - center_y,
                                ),
                                Angle(0),
                            )
                        )
                else:  # if there's only one coordinate then it's a circular hole and the vertex is the same as the pad center
                    vertices.append(
                        Vertex(
                            Position(
                                x=0,
                                y=0,
                            ),
                            Angle(0),
                        )
                    )
                pad_hole = PadHole(
                    uuid=str(uuid4()),
                    diameter=DrillDiameter(drill_diameter),
                    vertices=vertices,
                )
                holes.append(pad_hole)

            # Per https://github.com/dillonHe/EasyEDA-Documents/blob/master/Open-File-Format/PCB.md
            # shape: ELLIPSE/RECT/OVAL/POLYGON
            shape: Shape = Shape.ROUNDED_RECT
            shape_radius: ShapeRadius = ShapeRadius(0)
            if ee_shape_str == "RECT":
                shape = Shape.ROUNDED_RECT
            elif ee_shape_str in ("OVAL", "ELLIPSE"):
                shape_radius = ShapeRadius(1.0)
            elif ee_shape_str == "POLYGON":
                shape = Shape.POLYGON
            else:
                logger.error(
                    f"Warning: Unknown EasyEDA pad shape '{ee_shape_str}'. Defaulting to Shape.ROUNDED_RECT."
                )

            # # Mask margins - need to fetch from layer properties
            # solder_mask_margin, paste_mask_margin = None, None
            # # This is a simplification. Real systems might have per-pad overrides or complex rules.
            # for _, (mask_type, expansion) in self.mask_layer_properties.items():
            #     if expansion is not None:
            #         if mask_type in [
            #             LayerType.TOP_SOLDER_MASK,
            #             LayerType.BOTTOM_SOLDER_MASK,
            #         ]:
            #             solder_mask_margin = expansion * UNIT_SCALE
            #         elif mask_type in [
            #             LayerType.TOP_PASTE_MASK,
            #             LayerType.BOTTOM_PASTE_MASK,
            #         ]:
            #             paste_mask_margin = expansion * UNIT_SCALE
            package_pad = PackagePad(uuid=str(uuid4()), name=Name(pad_number))

            footprint_pad = FootprintPad(
                uuid=str(uuid4()),
                side=side,
                shape=shape,
                position=Position(x=center_x, y=center_y),
                rotation=Rotation(float(rotation_str) if rotation_str else 0.0),
                size=Size(width, height),
                radius=shape_radius,
                stop_mask=StopMaskConfig(StopMaskConfig.AUTO),
                solder_paste=SolderPasteConfig.OFF if holes else SolderPasteConfig.AUTO,
                copper_clearance=CopperClearance(0.0),
                function=PadFunction.STANDARD_PAD,
                package_pad=PackagePadUuid(package_pad.uuid),
                holes=holes,
            )

            return Pad(footprint_pad, package_pad)
        except Exception as e:
            logger.error(f"Error parsing PAD string '{'~'.join(parts)}': {e}")
            return None

    def _parse_track(self, parts: List[str]) -> Optional[Polygon]:
        # TRACK~strokeWidth~layerId~net~points~id~isLocked
        # points: "X1 Y1 X2 Y2 X3 Y3..."
        try:
            stroke_width = float(parts[1]) * UNIT_SCALE
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
                logger.error(
                    f"Warning: Invalid points for TRACK '{points_str}'. Skipping."
                )
                return None

            vertices: List[Position] = []
            for i in range(0, len(raw_coords), 2):
                vertices.append(
                    Position(x=self.xpos(raw_coords[i]), y=self.ypos(raw_coords[i + 1]))
                )

            polygon = Polygon(
                uuid=str(uuid4()),
                layer=track_layer,
                width=Width(stroke_width),
                fill=Fill(
                    False
                    # True if track_layer.layer not in self.unfilled_layers else False
                ),
                grab_area=GrabArea(False),
            )
            for vertex in vertices:
                polygon.add_vertex(Vertex(position=vertex, angle=Angle(0)))
            return polygon

        except Exception as e:
            logger.error(f"Error parsing TRACK string '{'~'.join(parts)}': {e}")
            return None

    def _parse_circle_primitive(self, parts: List[str]) -> Optional[Circle]:
        # CIRCLE~cx~cy~radius~strokeWidth~layerId~id~isLocked~~ (last empty field in example)
        try:
            cx = self.xpos(parts[1])
            cy = self.ypos(parts[2])
            radius = float(parts[3]) * UNIT_SCALE
            stroke_width = float(parts[4]) * UNIT_SCALE
            layer_id_str = parts[5]

            circle_layer = self.layer_map.get(layer_id_str)
            if not circle_layer:
                print(
                    f"Warning: Unknown layer ID '{layer_id_str}' for CIRCLE. Skipping."
                )
                return None

            return Circle(
                uuid=str(uuid4()),
                layer=circle_layer,
                width=Width(stroke_width),
                fill=Fill(False),
                grab_area=GrabArea(False),
                diameter=Diameter(radius * 2),
                position=Position(cx, cy),
            )

        except Exception as e:
            logger.error(f"Error parsing CIRCLE string '{'~'.join(parts)}': {e}")
            return None

    def _parse_arc_primitive(self, parts: List[str]) -> Optional[Polygon]:
        # ARC~strokeWidth~layerId~net~path~helperDots~id~isLocked
        # path is an SVG path string, e.g., "M X Y A RX RY XROT LARGEARC SWEEP X Y"
        try:
            stroke_width = float(parts[1]) * UNIT_SCALE
            layer_id_str = parts[2]
            # net = parts[3]
            path_str = parts[4]

            arc_layer = self.layer_map.get(layer_id_str)
            if not arc_layer:
                print(f"Warning: Unknown layer ID '{layer_id_str}' for ARC. Skipping.")
                return None

            import math
            import re

            def parse_svg_path_commands(path_str: str):
                """
                Parses an SVG path string into a list of commands and their parameters.
                This is a more robust method than simple splitting.

                Args:
                    path_str: The string from the 'd' attribute of an SVG <path>.

                Returns:
                    A list of dictionaries, where each dictionary represents a command.
                    e.g., [{'command': 'M', 'params': [x, y]}, {'command': 'A', ...}]
                """
                # This regex finds a command letter followed by any characters that are not a command letter.
                # It correctly handles optional whitespace and commas.
                COMMANDS = re.compile(
                    "([MmLlHhVvCcSsQqTtAaZz])([^MmLlHhVvCcSsQqTtAaZz]*)"
                )

                # This regex finds floating point numbers in the parameter string.
                # After (Correct and idiomatic)
                FLOATS = re.compile(r"[-+]?[0-9]*\.?[0-9]+")

                commands = []
                for command, params_str in COMMANDS.findall(path_str):
                    params = [float(p) for p in FLOATS.findall(params_str)]
                    commands.append({"command": command, "params": params})

                return commands

            # Parse using the robust function
            parsed_commands = parse_svg_path_commands(path_str)

            # Extract your values from the parsed structure
            if (
                len(parsed_commands) == 2
                and parsed_commands[0]["command"].upper() == "M"
                and parsed_commands[1]["command"].upper() == "A"
            ):
                move_params = parsed_commands[0]["params"]
                arc_params = parsed_commands[1]["params"]

                x1, y1 = self.xpos(move_params[0]), self.ypos(move_params[1])
                rx, ry = arc_params[0] * UNIT_SCALE, arc_params[1] * UNIT_SCALE
                rotation = arc_params[2]
                large_arc_flag = int(arc_params[3])
                sweep_flag = int(arc_params[4])
                x2, y2 = self.xpos(arc_params[5]), self.ypos(arc_params[6])

            def calculate_arc_center(
                start,
                end,
                radius,
                large_arc_flag: bool = False,
                sweep_flag: bool = True,
            ):
                """
                Calculate the center of the circle that contains an arc between two points.

                Args:
                    start: (x1, y1) starting point
                    end: (x2, y2) ending point
                    radius: radius of the circle
                    large_arc_flag: whether to use the larger arc (> π)
                    sweep_flag: True for counter-clockwise, False for clockwise

                Returns:
                    (cx, cy): center coordinates of the circle
                """
                x1, y1 = start
                x2, y2 = end

                # Chord vector and length
                dx = x2 - x1
                dy = y2 - y1
                L = math.hypot(dx, dy)

                # Ensure the arc is geometrically possible
                if L > 2 * radius:
                    raise ValueError(
                        f"No circle with radius {radius} can connect points {L / 2:.3f} units apart"
                    )

                if L == 0:
                    raise ValueError("Start and end points are identical")

                # Midpoint of the chord
                mx = (x1 + x2) / 2
                my = (y1 + y2) / 2

                # Distance from midpoint to center along perpendicular bisector
                # Using Pythagorean theorem: radius² = (L/2)² + h²
                h = math.sqrt(radius**2 - (L / 2) ** 2)

                # Unit vector perpendicular to the chord
                # Rotate the chord vector 90° counter-clockwise: (dx, dy) → (-dy, dx)
                perp_x = -dy / L
                perp_y = dx / L

                # There are two possible centers, one on each side of the chord
                center1 = (mx + h * perp_x, my + h * perp_y)
                center2 = (mx - h * perp_x, my - h * perp_y)

                # Choose the correct center based on the flags
                # For SVG arcs, we need to consider both large_arc_flag and sweep_flag
                if large_arc_flag == sweep_flag:
                    return center2
                else:
                    return center1

            def subtended_angle(
                start, end, radius, large_arc_flag: bool, sweep_flag: bool
            ):
                """
                Calculates the subtended angle of an arc, considering direction.

                Args:
                    start: (x1, y1) tuple
                    end: (x2, y2) tuple
                    radius: The circle's radius
                    large_arc_flag: True for the arc > 180 degrees
                    sweep_flag: True for counter-clockwise (positive angle) sweep

                Returns:
                    The subtended angle in radians, with a sign indicating direction.
                """
                x1, y1 = start
                x2, y2 = end

                # Chord length
                dx = x2 - x1
                dy = y2 - y1
                L = math.hypot(dx, dy)

                # Ensure the arc is possible
                if L > 2 * radius:
                    raise ValueError("No circle with radius R can connect these points")

                # Central angle in radians
                theta = 2 * math.asin(L / (2 * radius))
                if large_arc_flag:
                    theta = 2 * math.pi - theta

                # Apply the direction based on the sweep_flag
                # sweep_flag=1 is CCW (positive), sweep_flag=0 is CW (negative)
                # but the y-axis is upside down
                if sweep_flag:
                    theta = -theta

                return theta  # In radians

            # Example
            A = (x1, y1)
            B = (x2, y2)
            R = rx  # Try different radius values here

            theta_rad = subtended_angle(A, B, R, large_arc_flag, sweep_flag)
            theta_deg = math.degrees(theta_rad)

            print(f"Angle in radians: {theta_rad}")
            print(f"Angle in degrees: {theta_deg}")

            print(f"Points: A{A}, B{B}")
            print(f"Radius: {R}")
            print(self.offset_x, self.offset_y)
            center = calculate_arc_center(A, B, R, large_arc_flag, sweep_flag)
            angle = subtended_angle(A, B, R, large_arc_flag, sweep_flag)

            print(f"large_arc={large_arc_flag}, sweep={sweep_flag}:")
            print(f"  Center: ({center[0]:.3f}, {center[1]:.3f})")
            print(f"  Subtended angle: {math.degrees(angle):.1f}°")

            # Verify the center is correct distance from both points
            dist_A = math.hypot(center[0] - A[0], center[1] - A[1])
            dist_B = math.hypot(center[0] - B[0], center[1] - B[1])
            print(f"  Verification - Distance to A: {dist_A:.6f}, to B: {dist_B:.6f}")
            return Polygon(
                layer=arc_layer,
                uuid=str(uuid4()),
                fill=Fill(False),
                width=Width(stroke_width),
                grab_area=GrabArea(False),
                vertices=[
                    Vertex(position=Position(x1, y1), angle=Angle(math.degrees(angle))),
                    Vertex(position=Position(x2, y2), angle=Angle(0)),
                ],
            )

        except Exception as e:
            print(f"Error parsing ARC string '{'~'.join(parts)}': {e}")
            return None

    def _parse_solidregion(self, parts: List[str]) -> Optional[Polygon]:
        # SOLIDREGION~layerId~~Path~Type~RepID~~~~locked
        # Example: SOLIDREGION~100~~M390...Z~solid~rep3~~~~0
        # Indices:    0          1   2  3    4    5      6 7 8 9
        try:
            layer_id_str = parts[1]
            path_str = parts[3]
            solid = parts[4] != ""  # e.g., "solid"
            poly_layer = self.layer_map.get(layer_id_str)
            if not poly_layer:
                print(
                    f"Warning: Unknown layer ID '{layer_id_str}' for SOLIDREGION. Skipping."
                )
                return None

            vertices = self.parse_svg_path_to_points(path_str)
            if not vertices or len(vertices) < 3:
                logger.error(
                    f"Warning: Not enough vertices for SOLIDREGION '{path_str}'. Skipping."
                )
                return None

            polygon = Polygon(
                uuid=str(uuid4()),
                layer=poly_layer,
                width=Width(0),
                fill=Fill(
                    True
                    if all([poly_layer.layer not in self.unfilled_layers, solid])
                    else False
                ),
                grab_area=GrabArea(False),
            )
            for vertex in vertices:
                polygon.add_vertex(Vertex(position=vertex, angle=Angle(0)))

            return polygon
        except Exception as e:
            logger.error(f"Error parsing SOLIDREGION string '{'~'.join(parts)}': {e}")
            return None

    def _add_name_value_labels(
        self, height: float, polygons: List[Polygon]
    ) -> Tuple[StrokeText]:
        OFFSET = 1.2
        ymax, ymin = (0, 0)
        for polygon in polygons:
            if polygon.layer.layer == Layer("top_package_outlines").layer:
                for vertex in polygon.vertices:
                    ymax = vertex.position.y if vertex.position.y > ymax else ymax
                    ymin = vertex.position.y if vertex.position.y < ymin else ymin

        name = StrokeText(
            uuid=str(uuid4()),
            layer=Layer("top_names"),
            height=Height(1.0),
            stroke_width=StrokeWidth(0.2),
            letter_spacing=LetterSpacing.AUTO,
            line_spacing=LineSpacing.AUTO,
            align=Align("center bottom"),
            position=Position(0.0, ymax + OFFSET),
            rotation=Rotation(0.0),
            auto_rotate=AutoRotate(True),
            mirror=Mirror(False),
            value=Value("{{NAME}}"),
        )

        value = StrokeText(
            uuid=str(uuid4()),
            layer=Layer("top_values"),
            height=Height(1.0),
            stroke_width=StrokeWidth(0.2),
            letter_spacing=LetterSpacing.AUTO,
            line_spacing=LineSpacing.AUTO,
            align=Align("center top"),
            position=Position(0.0, ymin - OFFSET),
            rotation=Rotation(0.0),
            auto_rotate=AutoRotate(True),
            mirror=Mirror(False),
            value=Value("{{VALUE}}"),
        )
        return (name, value)

    # def _parse_text_primitive(
    #     self, parts: List[str]
    # ) -> Optional[Text]:
    #     # TEXT~type~centerX~centerY~strokeWidth~rotation~mirror~layerId~net~fontSize~display~text~path~id~locked
    #     # type: N (name), P (prefix/value)
    #     # mirror: 0 or 1
    #     # display: "FILTER" "ALWAYS" etc. or empty string for visible
    #     try:
    #         # text_type_indicator = parts[1] # e.g. "REF", "VAL" if available
    #         center_x = float(parts[2]) * UNIT_SCALE- offset_x
    #         center_y = float(parts[3]) * UNIT_SCALE- offset_y
    #         stroke_width = float(parts[4]) * UNIT_SCALE
    #         rotation = float(parts[5]) if parts[5] else 0.0
    #         mirrored = parts[6] == "1"
    #         layer_id_str = parts[7]
    #         # net = parts[8]
    #         font_height = (
    #             float(parts[9]) * UNIT_SCALE
    #         )  # EasyEDA font_size is height
    #         # display_flag = parts[10]
    #         text_content = parts[11]

    #         text_layer = self.layer_map.get(layer_id_str)
    #         if not text_layer:
    #             print(
    #                 f"Warning: Unknown layer ID '{layer_id_str}' for TEXT '{text_content}'. Skipping."
    #             )
    #             return None

    #         return Text(
    #             text=text_content,
    #             position=Position(x=center_x, y=center_y),
    #             font_height=font_height,
    #             stroke_width=stroke_width,
    #             rotation=rotation,
    #             mirrored=mirrored,
    #             visible=True,  # TODO: Parse display_flag for visibility
    #             layer=text_layer,
    #             horizontal_align=TextAlignHorizontal.CENTER,  # EasyEDA text anchor often center
    #             vertical_align=TextAlignVertical.MIDDLE,  # EasyEDA text anchor often middle
    #         )
    #     except Exception as e:
    #         print(f"Error parsing TEXT string '{'~'.join(parts)}': {e}")
    #         return None

    def _parse_hole_primitive(self, parts: List[str]) -> Optional[Hole]:
        # HOLE~X~Y~Radius~TRACKID~NET~ID~LOCKED
        # Example from parameters_easyeda.py: EeFootprintHole
        # center_x, center_y, radius, id, is_locked
        try:
            center_x = self.xpos(parts[1])
            center_y = self.ypos(parts[2])
            radius = float(parts[3]) * UNIT_SCALE

            hole = Hole(
                uuid=str(uuid4()),
                diameter=DrillDiameter(radius * 2),
                stop_mask=StopMaskConfig(StopMaskConfig.AUTO),
                vertices=[
                    Vertex(position=Position(center_x, center_y), angle=Angle(0))
                ],
            )

            return hole
        except Exception as e:
            logger.error(f"Error parsing HOLE string '{'~'.join(parts)}': {e}")
            return None

    # def _parse_rect_primitive(
    #     self, parts: List[str]
    # ) -> Optional[Rectangle]:
    #     # RECT~X~Y~Width~Height~strokeWidth~ID~LayerID~Locked
    #     # (from parameters_easyeda.py EeFootprintRectangle)
    #     try:
    #         x = float(parts[1]) * UNIT_SCALE- offset_x  # Top-left X
    #         y = float(parts[2]) * UNIT_SCALE- offset_y  # Top-left Y
    #         width = float(parts[3]) * UNIT_SCALE
    #         height = float(parts[4]) * UNIT_SCALE
    #         stroke_width = float(parts[5]) * UNIT_SCALE
    #         layer_id_str = parts[7]

    #         rect_layer = self.layer_map.get(layer_id_str)
    #         if not rect_layer:
    #             print(f"Warning: Unknown layer ID '{layer_id_str}' for RECT. Skipping.")
    #             return None

    #         return Rectangle(
    #             position=Position(
    #                 x=x + width / 2, y=y + height / 2
    #             ),  # CDM uses center point
    #             width=width,
    #             height=height,
    #             stroke_width=stroke_width,
    #             filled=False,  # EasyEDA rects are typically outlines
    #             layer=rect_layer,
    #         )
    #     except Exception as e:
    #         print(f"Error parsing RECT string '{'~'.join(parts)}': {e}")
    #         return None

    def _parse_svgnode(self, parts: List[str]) -> Optional[Model3DWithOrigin]:
        svg_node = json.loads(parts[1])
        attrs_3d = svg_node.get("attrs", {})
        if attrs_3d.get("uuid"):
            uuid_3d = str(UUID(attrs_3d["uuid"]))
            origin = attrs_3d["c_origin"].split(",")
            origin_x = self.xpos(origin[0])
            origin_y = self.ypos(origin[1])
            position_3d = Position3D(origin_x, origin_y, 0)  # TODO handle Z height?
            rotation = Rotation3D(
                *[float(k) for k in attrs_3d["c_rotation"].split(",")]
            )
            model = Footprint3DModel(uuid=uuid_3d)
            return Model3DWithOrigin(
                model=model, position_3d=position_3d, rotation_3d=rotation
            )
        return None, None

    def parse_easyeda_json(
        self, easyeda_data: Dict[str, Any], library_part: LibraryPart
    ) -> Tuple[Optional[Package], float, float]:
        if "packageDetail" not in easyeda_data:
            logger.error("Error: 'packageDetail' not found in EasyEDA data.")
            return None

        package_detail = easyeda_data["packageDetail"]

        if "dataStr" not in package_detail or not package_detail["dataStr"]:
            logger.error("Error: 'dataStr' for footprint not found or is empty.")
            # This can happen if the component only has a symbol but no footprint
            return None  # Or return an empty Footprint object if that's desired

        data_str = package_detail["dataStr"]
        head = data_str.get("head", {})
        height = data_str.get("BBox", {}).get("height", 0) * UNIT_SCALE
        width = data_str.get("BBox", {}).get("width", 0) * UNIT_SCALE
        self._parse_layer_definitions(data_str.get("layers", []))

        # --- Metadata ---
        footprint_name = (
            head.get("c_para", {}).get("package")
            or head.get("name")
            or package_detail.get("title", "UnknownFootprint")
        )
        pkg_uuid = library_part.footprint.uuid
        fp_uuid = str(uuid4())

        author = head.get("c_para", {}).get("Contributor")

        created_at: Optional[datetime] = None
        utime = head.get("utime")
        if utime:
            try:
                created_at = datetime.fromtimestamp(int(utime))
                created_string: Created = created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                pass

        generated_by = f"EasyEDA Editor {head.get('editorVersion', 'unknown')}"

        keywords = (", ").join(easyeda_data.get("tags", []))
        part_para = easyeda_data["dataStr"]["head"]["c_para"]
        custom_attrs = {}
        c_para = head.get("c_para", {})
        c_para.update(part_para)
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
        self.offset_x = (
            offset_x_easyeda_units * UNIT_SCALE
        )  # Convert to mm for pad positioning
        self.offset_y = (
            offset_y_easyeda_units * UNIT_SCALE
        )  # Convert to mm for pad positioning
        print(f"Offset: {self.offset_x}, {self.offset_y}")
        fp = Footprint(
            uuid=fp_uuid,
            name=Name("default"),
            description=Description(""),
            position_3d=Position3D.zero(),
            rotation_3d=Rotation3D.zero(),
        )

        # custom_attributes=custom_attrs,
        # height=height,
        # width=width,
        # source_offset_x=offset_x_easyeda_units,  # Store original source units
        # source_offset_y=offset_y_easyeda_units,  # Store original source units

        package = Package(
            uuid=pkg_uuid,
            name=Name(footprint_name),
            description=Description(
                easyeda_data.get("description") + (json.dumps(c_para))
            ),
            created=Created(created_string),
            deprecated=Deprecated(False),
            categories=[Category("1d2630f1-c375-49f0-a0dc-2446735d82f4")],
            assembly_type=AssemblyType.AUTO,
            keywords=Keywords(keywords),
            author=Author(author),
            version=Version(DEFAULT_VERSION),
            generated_by=GeneratedBy(f"webparts:lcsc:{easyeda_data.get('lcsc_id', 'unknown')}"),
        )

        # --- Shapes ---
        # Things you can add to a Footprint
        #   pads=[],
        #   models_3d=[],
        #   polygons=[],
        #   circles=[],
        #   texts=[],
        #   holes=[],
        #   zones=[],
        for shape_str in data_str.get("shape", []):
            parts = shape_str.split("~")
            shape_type = parts[0]

            if shape_type == "PAD":
                footprint_pad, package_pad = self._parse_pad(parts)
                fp.add_pad(footprint_pad)
                package.add_pad(package_pad)
            elif shape_type == "TRACK":
                polygon = self._parse_track(parts)
                fp.add_polygon(polygon)
            elif shape_type == "CIRCLE":
                circle = self._parse_circle_primitive(parts)
                fp.add_circle(circle)
            elif shape_type == "ARC":
                circle = self._parse_arc_primitive(parts)
                fp.add_circle(circle)
                # Needs robust SVG arc parsing
            elif shape_type == "SOLIDREGION":
                polygon = self._parse_solidregion(parts)
                fp.add_polygon(polygon)
            # elif shape_type == "TEXT":
            #     element = self._parse_text_primitive(parts, offset_x, offset_y)
            elif shape_type == "HOLE":  # From prior art, implies standalone NPTH
                hole = self._parse_hole_primitive(parts)
                fp.add_hole(hole)
            # elif shape_type == "RECT":  # From prior art, non-pad rectangle
            #     element = self._parse_rect_primitive(parts, offset_x, offset_y)
            elif shape_type == "SVGNODE":
                model, position_3d, rotation_3d = self._parse_svgnode(parts)
                fp.add_3d_model(model)
                package.add_3d_model(
                    Package3DModel(uuid=model.uuid, name=Name("EasyEDA"))
                )
                fp.position_3d = position_3d
                fp.rotation_3d = rotation_3d
            # elif shape_type == "VIA": # VIA specific parsing if needed
            #     element = self._parse_via_primitive(parts, offset_x, offset_y)
            else:
                print(f"Notice: Unhandled EasyEDA shape type: {shape_type}")

        if fp.pads:
            texts = self._add_name_value_labels(height, fp.polygons)
            for text in texts:
                fp.add_text(text)
        package.add_footprint(fp)
        return package, self.offset_x, self.offset_y
