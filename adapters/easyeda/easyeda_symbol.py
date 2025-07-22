import logging
from datetime import datetime
from math import ceil, floor
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID, uuid4

from librepcb_parts_generator.entities.common import (
    Align,
    Angle,
    Author,
    Category,
    Created,
    Deprecated,
    Description,
    Fill,
    GeneratedBy,
    GrabArea,
    Height,
    Keywords,
    Layer,
    Length,
    Name,
    Polygon,
    Position,
    Rotation,
    Text,
    Value,
    Version,
    Vertex,
    Width,
)
from librepcb_parts_generator.entities.symbol import (
    NameAlign,
    NameHeight,
    NamePosition,
    NameRotation,
    Pin,
    Symbol,
)

logger = logging.getLogger(__name__)


# There are 10 pixels to a grid unit
UNIT_SCALE = 0.1
GRID_SIZE = 2.54

# Define Number for type hinting
Number = Union[int, float]


class EasyEDASymbolParser:
    def __init__(self):
        self.offset_x = 0.0
        self.offset_y = 0.0

    def xpos(self, cx: Number) -> float:
        return float(cx) * UNIT_SCALE - self.offset_x

    def ypos(self, cy: Number) -> float:
        return (float(cy) * UNIT_SCALE - self.offset_y) * -1

    def _parse_custom_attributes(self, attr_str: str) -> Dict[str, str]:
        """Parse EasyEDA custom attributes string like 'package`LED3MM`nameAlias`Model`'"""
        attrs = {}
        if not attr_str:
            return attrs

        parts = attr_str.split("`")
        for i in range(0, len(parts) - 1, 2):
            if i + 1 < len(parts):
                key = parts[i]
                value = parts[i + 1]
                attrs[key] = value
        return attrs

    def _parse_pin(self, pin_str: str) -> Optional[Tuple[str, str, Pin]]:
        """Parse EasyEDA pin string into a tuple of (pin_name, pin_number, Pin)."""
        segments = pin_str.split("^^")
        if len(segments) < 7:
            return None

        config_parts = segments[0].split("~")
        if len(config_parts) < 8:
            return None

        # Extract pin number (designator)
        pin_number = config_parts[3]

        # Extract pin name
        name_parts = segments[3].split("~")
        pin_name = name_parts[4] if len(name_parts) > 4 else ""

        x = floor(self.xpos(config_parts[4]))
        y = floor(self.ypos(config_parts[5]))
        rotation = (int(config_parts[6] if config_parts[6] else "0") - 180) % 360

        path_parts = segments[2].split("~")[0].split()
        pin_line = path_parts[-1]
        distance = ceil(float(pin_line) * UNIT_SCALE)

        final_x = x * GRID_SIZE
        final_y = y * GRID_SIZE
        final_distance = abs(GRID_SIZE * distance)
        pin = Pin(
            uuid=str(uuid4()),
            name=Name(pin_name),
            position=Position(final_x, final_y),
            rotation=Rotation(rotation),
            length=Length(final_distance),
            name_height=NameHeight(GRID_SIZE * 0.9),
            name_align=NameAlign("left center"),
            name_position=NamePosition(final_distance + GRID_SIZE * 0.5, 0),
            name_rotation=NameRotation(0),
        )
        return pin_name, pin_number, pin

    # def _parse_line(
    #     self, parts: List[str], offset_x: float, offset_y: float
    # ) -> Optional[Polygon]:
    #     """Parse EasyEDA line: L~x1~y1~x2~y2~strokeColor~strokeWidth~strokeStyle~fillColor~id~locked"""
    #     try:
    #         x1 = float(parts[1]) * UNIT_SCALE - offset_x
    #         y1 = float(parts[2]) * UNIT_SCALE - offset_y
    #         x2 = float(parts[3]) * UNIT_SCALE - offset_x
    #         y2 = float(parts[4]) * UNIT_SCALE - offset_y
    #         stroke_width = float(parts[6]) if parts[6] else 0.0

    #         return Line(
    #             start=Point(x=x1, y=y1),
    #             end=Point(x=x2, y=y2),
    #             width=stroke_width,
    #             layer=LayerRef(
    #                 type=LayerType.DOCUMENTATION
    #             ),  # Default layer for symbols
    #         )
    #     except Exception as e:
    #         print(f"Error parsing line: {e}")
    #         return None

    def _parse_rectangle(self, parts: List[str]) -> Optional[Polygon]:
        """Parse EasyEDA rectangle: R~x~y~rx~ry~width~height~strokeColor~strokeWidth~strokeStyle~fillColor~id~locked"""
        try:
            x = floor(self.xpos(parts[1])) * GRID_SIZE
            y = floor(self.ypos(parts[2])) * GRID_SIZE
            width = float(parts[5]) * UNIT_SCALE * GRID_SIZE
            height = float(parts[6]) * UNIT_SCALE * GRID_SIZE
            stroke_width = float(parts[8]) if parts[8] else 0.0
            filled = parts[10] != "none" and parts[10] != ""

            vertices = []
            (vertices.append(Vertex(position=Position(x=x, y=y), angle=Angle(0))),)
            (
                vertices.append(
                    Vertex(position=Position(x=x + width, y=y), angle=Angle(0))
                ),
            )
            (
                vertices.append(
                    Vertex(position=Position(x=x + width, y=y - height), angle=Angle(0))
                ),
            )
            (
                vertices.append(
                    Vertex(position=Position(x=x, y=y - height), angle=Angle(0))
                ),
            )
            vertices.append(Vertex(position=Position(x=x, y=y), angle=Angle(0)))
            vertices.append(vertices[0])
            polygon = Polygon(
                uuid=str(uuid4()),
                width=Width(0.2),
                layer=Layer("sym_outlines"),
                fill=Fill(False),
                grab_area=GrabArea(True),
                vertices=vertices,
            )
            return polygon
        except Exception as e:
            print(f"Error parsing rectangle: {e}")
            return None

    # # Add this method to handle ellipses:
    # def _parse_ellipse(
    #     self, parts: List[str], offset_x: float, offset_y: float
    # ) -> Optional[Ellipse]:
    #     """Parse EasyEDA ellipse: E~cx~cy~rx~ry~strokeColor~strokeWidth~strokeStyle~fillColor~id~locked"""
    #     try:
    #         cx = float(parts[1]) * UNIT_SCALE - offset_x
    #         cy = float(parts[2]) * UNIT_SCALE - offset_y
    #         rx = float(parts[3]) * UNIT_SCALE
    #         ry = float(parts[4]) * UNIT_SCALE
    #         stroke_width = float(parts[6]) if len(parts) > 6 and parts[6] else 0.0
    #         filled = len(parts) > 8 and parts[8] != "none" and parts[8] != ""

    #         return Ellipse(
    #             center=Point(x=cx, y=cy),
    #             radius_x=rx,
    #             radius_y=ry,
    #             stroke_width=stroke_width,
    #             filled=filled,
    #             layer=LayerRef(type=LayerType.DOCUMENTATION),
    #         )
    #     except Exception as e:
    #         print(f"Error parsing ellipse: {e}")
    #         return None

    # def _parse_circle(
    #     self, parts: List[str], offset_x: float, offset_y: float
    # ) -> Optional[Circle]:
    #     """Parse EasyEDA circle: C~cx~cy~r~strokeColor~strokeWidth~strokeStyle~fillColor~id~locked"""
    #     try:
    #         cx = float(parts[1]) * UNIT_SCALE - offset_x
    #         cy = float(parts[2]) * UNIT_SCALE - offset_y
    #         radius = float(parts[3]) * UNIT_SCALE
    #         stroke_width = float(parts[5]) if parts[5] else 0.0
    #         filled = parts[7] != "none" and parts[7] != ""

    #         return Circle(
    #             center=Point(x=cx, y=cy),
    #             radius=radius,
    #             stroke_width=stroke_width,
    #             filled=filled,
    #             layer=LayerRef(type=LayerType.DOCUMENTATION),
    #         )
    #     except Exception as e:
    #         print(f"Error parsing circle: {e}")
    #         return None

    # def _parse_text(
    #     self, parts: List[str], offset_x: float, offset_y: float
    # ) -> Optional[Text]:
    #     """Parse EasyEDA text: T~mark~x~y~rotation~color~fontFamily~fontSize~fontWeight~fontStyle~baseline~textType~string~visible~textAnchor~id~locked"""
    #     try:
    #         mark = parts[1]  # L=label, N=name, P=prefix
    #         x = float(parts[2]) * UNIT_SCALE - offset_x
    #         y = float(parts[3]) * UNIT_SCALE - offset_y
    #         rotation = float(parts[4]) if parts[4] else 0.0
    #         font_size = float(parts[7].replace("pt", "")) if parts[7] else 12.0
    #         text_content = parts[11]
    #         visible = parts[12] == "1" if len(parts) > 12 else True

    #         # Convert font size from pt to mm (1 pt ≈ 0.353 mm)
    #         font_height_mm = font_size * 0.353

    #         return Text(
    #             text=text_content,
    #             position=Point(x=x, y=y),
    #             font_height=font_height_mm,
    #             stroke_width=0.1,  # Default
    #             rotation=rotation,
    #             visible=visible,
    #             text_type=mark,
    #             layer=LayerRef(type=LayerType.DOCUMENTATION),
    #         )
    #     except Exception as e:
    #         print(f"Error parsing text: {e}")
    #         return None

    def _parse_polyline(
        self,
        parts: List[str],
    ) -> Optional[Polygon]:
        """Parse EasyEDA polyline: PL~points~strokeColor~strokeWidth~strokeStyle~fillColor~id~locked"""
        try:
            points_str = parts[1]
            stroke_width = float(parts[3]) if parts[3] else 0.0

            # Parse points "x1 y1 x2 y2 x3 y3..."
            coords = [float(c) for c in points_str.split() if c]
            if len(coords) < 4 or len(coords) % 2 != 0:
                return None

            vertices = []
            for i in range(0, len(coords), 2):
                x = floor(self.xpos(coords[i])) * GRID_SIZE
                y = floor(self.ypos(coords[i + 1])) * GRID_SIZE
                vertices.append(Vertex(position=Position(x=x, y=y), angle=Angle(0)))
            vertices.append(vertices[0])
            polygon = Polygon(
                uuid=str(uuid4()),
                width=Width(0.2),
                layer=Layer("sym_outlines"),
                fill=Fill(False),
                grab_area=GrabArea(True),
                vertices=vertices,
            )
            return polygon
        except Exception as e:
            print(f"Error parsing polyline: {e}")
            return None

    def parse_easyeda_symbol(self, easyeda_data: Dict[str, Any]) -> Optional[Symbol]:
        """Parse EasyEDA symbol data to CDM Symbol."""
        data_str = easyeda_data.get("dataStr", {})
        if not data_str:
            return None

        head = data_str.get("head", {})
        shapes = data_str.get("shape", [])
        uuid = str(UUID(head["uuid"]))
        # Parse head information
        if isinstance(head, str):
            # Parse head string format: "7~1.7.5~400~300~package`DIP08`nameDisplay`0`..."
            head_parts = head.split("~")
            doc_type = head_parts[0] if head_parts else ""
            doc_version = head_parts[1] if len(head_parts) > 1 else ""
            origin_x = float(head_parts[2]) if len(head_parts) > 2 else 0
            origin_y = float(head_parts[3]) if len(head_parts) > 3 else 300.0
            custom_attrs_str = "~".join(head_parts[4:]) if len(head_parts) > 4 else ""
        else:
            # Dict format
            origin_x = head["x"]
            origin_y = head["y"]
            custom_attrs_str = ""
        # Parse custom attributes
        custom_attrs = self._parse_custom_attributes(custom_attrs_str)
        symbol_name = custom_attrs.get(
            "name", easyeda_data.get("title", "Unknown Symbol")
        )
        package_name = custom_attrs.get("package")
        prefix = custom_attrs.get("pre", "U")
        spice_prefix = custom_attrs.get("spicePre")
        model_name = custom_attrs.get("Model", custom_attrs.get("nameAlias"))

        self.offset_x = origin_x * UNIT_SCALE
        self.offset_y = origin_y * UNIT_SCALE

        print(f"Offset: ({self.offset_x}, {self.offset_y})")
        # First pass: collect raw pin data

        # Create symbol and add final, centered pins
        symbol = Symbol(
            uuid=uuid,
            name=Name(easyeda_data.get("title", "Unknown")),
            description=Description(easyeda_data.get("description", "")),
            keywords=Keywords(", ".join(easyeda_data.get("tags", []))),
            author=Author(head.get("c_para", {}).get("Contributor", "EasyEDA User")),
            version=Version("0.1.0"),
            created=Created(datetime.now()),
            deprecated=Deprecated(False),
            generated_by=GeneratedBy(f"webparts:lcsc:{easyeda_data.get('lcsc_id', 'unknown')}"),
            categories=[Category("e29f0cb3-ef6d-4203-b854-d75150cbae0b")],
        )

        pin_data_list = []
        for shape_str in shapes:
            parts = shape_str.split("~")
            if not parts:
                continue

            shape_type = parts[0]

            if shape_type == "P":  # Pin
                pin_data = self._parse_pin(shape_str)
                if pin_data:
                    pin_data_list.append(pin_data)
                    _, _, pin_object = pin_data
                    symbol.add_pin(pin_object)

            # elif shape_type == "L":  # Line
            #     line = self._parse_line(parts)
            #     if line:
            #         symbol.graphics.append(line)

            elif shape_type == "R":  # Rectangle
                rect = self._parse_rectangle(parts)
                if rect:
                    symbol.add_polygon(rect)

            # elif shape_type == "C":  # Circle
            #     circle = self._parse_circle(parts)
            #     if circle:
            #         symbol.graphics.append(circle)

            # elif shape_type == "E":  # Ellipse
            #     ellipse = self._parse_ellipse(parts)
            #     if ellipse:
            #         symbol.graphics.append(ellipse)

            # elif shape_type == "T":  # Text
            #     text = self._parse_text(parts)
            #     if text:
            #         symbol.graphics.append(text)

            # elif shape_type == "PL":  # Polyline
            #     polyline = self._parse_polyline(parts)
            #     if polyline:
            #         symbol.add_polygon(polyline)

            elif shape_type == "PG":  # Polygon
                polyline = self._parse_polyline(parts)
                if polyline:
                    symbol.add_polygon(polyline)

            else:
                print(f"Unhandled symbol shape type: {shape_type}")

        # Add name and value labels
        texts = self._add_name_value_labels(symbol.polygons)

        for text in texts:
            symbol.add_text(text)

        return symbol, pin_data_list

    def _add_name_value_labels(self, polygons: List[Polygon]) -> Tuple[Text]:
        OFFSET = 1.2
        # Define thresholds for large symbols (in grid units)
        LARGE_WIDTH_THRESHOLD = 20
        LARGE_HEIGHT_THRESHOLD = 20

        if polygons:
            xmax, xmin = (float("-inf"), float("inf"))
            ymax, ymin = (float("-inf"), float("inf"))
            for polygon in polygons:
                if polygon.layer.layer == Layer("sym_outlines").layer:
                    for vertex in polygon.vertices:
                        xmax = max(xmax, vertex.position.x)
                        xmin = min(xmin, vertex.position.x)
                        ymax = max(ymax, vertex.position.y)
                        ymin = min(ymin, vertex.position.y)
        else:
            # Handle cases where there are no polygons, e.g., for symbols with only pins
            xmax, xmin = (2 * GRID_SIZE, -2 * GRID_SIZE)
            ymax, ymin = (GRID_SIZE, -GRID_SIZE)

        width = xmax - xmin
        height = ymax - ymin

        # Check if the symbol is large
        if width > LARGE_WIDTH_THRESHOLD or height > LARGE_HEIGHT_THRESHOLD:
            # Place labels inside for large symbols
            name_y = ymax - (height / 3)
            value_y = ymin + (height / 3)
            name_align = "center center"
            value_align = "center center"
            name_position = Position(0.0, name_y)
            value_position = Position(0.0, value_y)
        else:
            # Place labels outside for small symbols
            name_position = Position(0.0, ymax + OFFSET)
            value_position = Position(0.0, ymin - OFFSET)
            name_align = "center bottom"
            value_align = "center top"

        name = Text(
            uuid=str(uuid4()),
            layer=Layer("sym_names"),
            height=Height(2.0),
            align=Align(name_align),
            position=name_position,
            rotation=Rotation(0.0),
            value=Value("{{NAME}}"),
        )

        value = Text(
            uuid=str(uuid4()),
            layer=Layer("sym_values"),
            height=Height(2.0),
            align=Align(value_align),
            position=value_position,
            rotation=Rotation(0.0),
            value=Value("{{VALUE}}"),
        )
        return (name, value)
