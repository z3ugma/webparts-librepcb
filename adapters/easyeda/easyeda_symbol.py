# adapters/easyeda_symbol.py
# Global imports
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from models.graphics import Circle, Ellipse, Line, Point, Polyline, Rectangle, Text
from models.layer import LayerRef, LayerType
from models.symbol import ElectricalType, Pin, PinDirection, Symbol


class EasyEDASymbolParser:
    def __init__(self):
        self.unit_scale = 0.1

        # Map EasyEDA electrical types to CDM
        self.electrical_type_map = {
            0: ElectricalType.UNDEFINED,
            1: ElectricalType.INPUT,
            2: ElectricalType.OUTPUT,
            3: ElectricalType.IO,
            4: ElectricalType.POWER,
        }

        # Map EasyEDA pin orientations (in degrees) to CDM directions
        self.direction_map = {
            0: PinDirection.RIGHT,  # 0°
            90: PinDirection.DOWN,  # 90°
            180: PinDirection.LEFT,  # 180°
            270: PinDirection.UP,  # 270°
        }

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

    def _parse_pin(
        self, pin_str: str, offset_x: float, offset_y: float
    ) -> Optional[Pin]:
        """Parse EasyEDA pin string."""
        # P~show~0~1~670~30~~gge23^^670~30^^M 670 30 h -20~#880000^^1~648~33~0~1~end~~11pt^^1~655~29~0~1~start~~11pt^^0~653~30^^0~M 650 27 L 647 30 L 650 33

        segments = pin_str.split("^^")
        if len(segments) < 7:
            print(f"Warning: Pin string has insufficient segments: {pin_str}")
            return None

        try:
            # Parse pin configuration
            config_parts = segments[0].split("~")
            if len(config_parts) < 8:
                return None

            display = config_parts[1]  # 'show' or ''
            electrical_type_num = int(config_parts[2]) if config_parts[2] else 0
            spice_pin_number = config_parts[3]
            pos_x = float(config_parts[4]) * self.unit_scale - offset_x
            pos_y = float(config_parts[5]) * self.unit_scale - offset_y

            rotation_str = config_parts[6] if config_parts[6] else "0"
            pin_id = config_parts[7]

            # Parse pin dot position (the connection point)
            dot_parts = segments[1].split("~")
            dot_x = float(dot_parts[0]) * self.unit_scale - offset_x
            dot_y = float(dot_parts[1]) * self.unit_scale - offset_y

            # Parse pin path to determine direction and length
            path_parts = segments[2].split("~")
            pin_path = path_parts[0]  # SVG path like "M 670 30 h -20"

            # Extract direction from rotation or path
            rotation = int(rotation_str) if rotation_str.isdigit() else 0
            direction = self.direction_map.get(rotation, PinDirection.RIGHT)

            # Parse pin name (segment 3)
            name_parts = segments[3].split("~")
            name_visible = name_parts[0] == "1"
            name_x = (
                float(name_parts[1]) * self.unit_scale - offset_x
                if name_parts[1]
                else pos_x
            )
            name_y = (
                float(name_parts[2]) * self.unit_scale - offset_y
                if name_parts[2]
                else pos_y
            )
            pin_name = (
                name_parts[4] if len(name_parts) > 4 else f"PIN_{spice_pin_number}"
            )

            # Parse pin number (segment 4)
            number_parts = segments[4].split("~")
            number_visible = number_parts[0] == "1"
            number_x = (
                float(number_parts[1]) * self.unit_scale - offset_x
                if number_parts[1]
                else pos_x
            )
            number_y = (
                float(number_parts[2]) * self.unit_scale - offset_y
                if number_parts[2]
                else pos_y
            )
            pin_number = number_parts[4] if len(number_parts) > 4 else spice_pin_number

            # Parse decorations (dot, clock)
            dot_parts = segments[5].split("~") if len(segments) > 5 else ["0"]
            inverted = dot_parts[0] == "1"

            clock_parts = segments[6].split("~") if len(segments) > 6 else ["0"]
            clock = clock_parts[0] == "1"

            return Pin(
                uuid=uuid4(),
                name=pin_name,
                number=pin_number,
                position=Point(x=pos_x, y=pos_y),
                direction=direction,
                electrical_type=self.electrical_type_map.get(
                    electrical_type_num, ElectricalType.UNDEFINED
                ),
                name_visible=name_visible,
                number_visible=number_visible,
                name_position=Point(x=name_x, y=name_y),
                number_position=Point(x=number_x, y=number_y),
                inverted=inverted,
                clock=clock,
                spice_number=spice_pin_number,
            )

        except Exception as e:
            print(f"Error parsing pin: {e}")
            print(f"Pin string: {pin_str}")
            return None

    def _parse_line(
        self, parts: List[str], offset_x: float, offset_y: float
    ) -> Optional[Line]:
        """Parse EasyEDA line: L~x1~y1~x2~y2~strokeColor~strokeWidth~strokeStyle~fillColor~id~locked"""
        try:
            x1 = float(parts[1]) * self.unit_scale - offset_x
            y1 = float(parts[2]) * self.unit_scale - offset_y
            x2 = float(parts[3]) * self.unit_scale - offset_x
            y2 = float(parts[4]) * self.unit_scale - offset_y
            stroke_width = float(parts[6]) if parts[6] else 0.0

            return Line(
                start=Point(x=x1, y=y1),
                end=Point(x=x2, y=y2),
                width=stroke_width,
                layer=LayerRef(
                    type=LayerType.DOCUMENTATION
                ),  # Default layer for symbols
            )
        except Exception as e:
            print(f"Error parsing line: {e}")
            return None

    def _parse_rectangle(
        self, parts: List[str], offset_x: float, offset_y: float
    ) -> Optional[Rectangle]:
        """Parse EasyEDA rectangle: R~x~y~rx~ry~width~height~strokeColor~strokeWidth~strokeStyle~fillColor~id~locked"""
        try:
            x = float(parts[1]) * self.unit_scale - offset_x
            y = float(parts[2]) * self.unit_scale - offset_y
            width = float(parts[5]) * self.unit_scale
            height = float(parts[6]) * self.unit_scale
            stroke_width = float(parts[8]) if parts[8] else 0.0
            filled = parts[10] != "none" and parts[10] != ""

            return Rectangle(
                position=Point(x=x + width / 2, y=y + height / 2),  # CDM uses center
                width=width,
                height=height,
                stroke_width=stroke_width,
                filled=filled,
                layer=LayerRef(type=LayerType.DOCUMENTATION),
            )
        except Exception as e:
            print(f"Error parsing rectangle: {e}")
            return None

    # Add this method to handle ellipses:
    def _parse_ellipse(
        self, parts: List[str], offset_x: float, offset_y: float
    ) -> Optional[Ellipse]:
        """Parse EasyEDA ellipse: E~cx~cy~rx~ry~strokeColor~strokeWidth~strokeStyle~fillColor~id~locked"""
        try:
            cx = float(parts[1]) * self.unit_scale - offset_x
            cy = float(parts[2]) * self.unit_scale - offset_y
            rx = float(parts[3]) * self.unit_scale
            ry = float(parts[4]) * self.unit_scale
            stroke_width = float(parts[6]) if len(parts) > 6 and parts[6] else 0.0
            filled = len(parts) > 8 and parts[8] != "none" and parts[8] != ""

            return Ellipse(
                center=Point(x=cx, y=cy),
                radius_x=rx,
                radius_y=ry,
                stroke_width=stroke_width,
                filled=filled,
                layer=LayerRef(type=LayerType.DOCUMENTATION),
            )
        except Exception as e:
            print(f"Error parsing ellipse: {e}")
            return None

    def _parse_circle(
        self, parts: List[str], offset_x: float, offset_y: float
    ) -> Optional[Circle]:
        """Parse EasyEDA circle: C~cx~cy~r~strokeColor~strokeWidth~strokeStyle~fillColor~id~locked"""
        try:
            cx = float(parts[1]) * self.unit_scale - offset_x
            cy = float(parts[2]) * self.unit_scale - offset_y
            radius = float(parts[3]) * self.unit_scale
            stroke_width = float(parts[5]) if parts[5] else 0.0
            filled = parts[7] != "none" and parts[7] != ""

            return Circle(
                center=Point(x=cx, y=cy),
                radius=radius,
                stroke_width=stroke_width,
                filled=filled,
                layer=LayerRef(type=LayerType.DOCUMENTATION),
            )
        except Exception as e:
            print(f"Error parsing circle: {e}")
            return None

    def _parse_text(
        self, parts: List[str], offset_x: float, offset_y: float
    ) -> Optional[Text]:
        """Parse EasyEDA text: T~mark~x~y~rotation~color~fontFamily~fontSize~fontWeight~fontStyle~baseline~textType~string~visible~textAnchor~id~locked"""
        try:
            mark = parts[1]  # L=label, N=name, P=prefix
            x = float(parts[2]) * self.unit_scale - offset_x
            y = float(parts[3]) * self.unit_scale - offset_y
            rotation = float(parts[4]) if parts[4] else 0.0
            font_size = float(parts[7].replace("pt", "")) if parts[7] else 12.0
            text_content = parts[11]
            visible = parts[12] == "1" if len(parts) > 12 else True

            # Convert font size from pt to mm (1 pt ≈ 0.353 mm)
            font_height_mm = font_size * 0.353

            return Text(
                text=text_content,
                position=Point(x=x, y=y),
                font_height=font_height_mm,
                stroke_width=0.1,  # Default
                rotation=rotation,
                visible=visible,
                text_type=mark,
                layer=LayerRef(type=LayerType.DOCUMENTATION),
            )
        except Exception as e:
            print(f"Error parsing text: {e}")
            return None

    def _parse_polyline(
        self, parts: List[str], offset_x: float, offset_y: float
    ) -> Optional[Polyline]:
        """Parse EasyEDA polyline: PL~points~strokeColor~strokeWidth~strokeStyle~fillColor~id~locked"""
        try:
            points_str = parts[1]
            stroke_width = float(parts[3]) if parts[3] else 0.0

            # Parse points "x1 y1 x2 y2 x3 y3..."
            coords = [float(c) for c in points_str.split() if c]
            if len(coords) < 4 or len(coords) % 2 != 0:
                return None

            points = []
            for i in range(0, len(coords), 2):
                x = coords[i] * self.unit_scale - offset_x
                y = coords[i + 1] * self.unit_scale - offset_y
                points.append(Point(x=x, y=y))

            return Polyline(
                points=points,
                stroke_width=stroke_width,
                layer=LayerRef(type=LayerType.DOCUMENTATION),
            )
        except Exception as e:
            print(f"Error parsing polyline: {e}")
            return None

    def parse_easyeda_symbol(self, easyeda_data: Dict[str, Any]) -> Optional[Symbol]:
        """Parse EasyEDA symbol data to CDM Symbol."""

        # Extract symbol data
        data_str = easyeda_data.get("dataStr", {})
        if not data_str:
            print("Error: No dataStr found in EasyEDA symbol data")
            return None

        head = data_str.get("head", {})
        shapes = data_str.get("shape", [])

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

        uuid = UUID(head["uuid"])

        # Parse custom attributes
        custom_attrs = self._parse_custom_attributes(custom_attrs_str)

        # Extract symbol properties
        symbol_name = custom_attrs.get(
            "name", easyeda_data.get("title", "Unknown Symbol")
        )
        package_name = custom_attrs.get("package")
        prefix = custom_attrs.get("pre", "U?")
        spice_prefix = custom_attrs.get("spicePre")
        model_name = custom_attrs.get("Model", custom_attrs.get("nameAlias"))

        # Create symbol
        symbol = Symbol(
            name=symbol_name,
            uuid=uuid,
            prefix=prefix,
            package_name=package_name,
            spice_prefix=spice_prefix,
            spice_model=model_name,
            default_value=model_name,
            description=easyeda_data.get("description"),
            keywords=easyeda_data.get("tags", []),
            custom_attributes=custom_attrs,
            origin=Point(x=origin_x, y=origin_y),
        )

        # Parse shapes
        offset_x = origin_x * self.unit_scale
        offset_y = origin_y * self.unit_scale

        for shape_str in shapes:
            parts = shape_str.split("~")
            if not parts:
                continue

            shape_type = parts[0]

            if shape_type == "P":  # Pin
                pin = self._parse_pin(shape_str, offset_x, offset_y)
                if pin:
                    symbol.pins.append(pin)

            elif shape_type == "L":  # Line
                line = self._parse_line(parts, offset_x, offset_y)
                if line:
                    symbol.graphics.append(line)

            elif shape_type == "R":  # Rectangle
                rect = self._parse_rectangle(parts, offset_x, offset_y)
                if rect:
                    symbol.graphics.append(rect)

            elif shape_type == "C":  # Circle
                circle = self._parse_circle(parts, offset_x, offset_y)
                if circle:
                    symbol.graphics.append(circle)

            elif shape_type == "E":  # Ellipse
                ellipse = self._parse_ellipse(parts, offset_x, offset_y)
                if ellipse:
                    symbol.graphics.append(ellipse)

            elif shape_type == "T":  # Text
                text = self._parse_text(parts, offset_x, offset_y)
                if text:
                    symbol.graphics.append(text)

            elif shape_type == "PL":  # Polyline
                polyline = self._parse_polyline(parts, offset_x, offset_y)
                if polyline:
                    symbol.graphics.append(polyline)

            else:
                print(f"Unhandled symbol shape type: {shape_type}")

        # Calculate bounding box
        if symbol.pins or symbol.graphics:
            min_x = min_y = float("inf")
            max_x = max_y = float("-inf")

            for pin in symbol.pins:
                min_x = min(min_x, pin.position.x)
                max_x = max(max_x, pin.position.x)
                min_y = min(min_y, pin.position.y)
                max_y = max(max_y, pin.position.y)

            # TODO: Add graphics bounds calculation

            if min_x != float("inf"):
                symbol.width = max_x - min_x
                symbol.height = max_y - min_y

        return symbol
