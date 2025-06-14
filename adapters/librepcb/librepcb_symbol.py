# adapters/librepcb_symbol.py

# Global imports
import os
import uuid as uuid_module
from datetime import datetime
from math import floor
from typing import List, Tuple

from models.footprint import Point
from models.symbol import PinDirection, Symbol

# Local imports
from .s_expression import SExpSymbol, serialize_to_sexpr
import constants as const

class LibrePCBSymbolSerializer:
    def __init__(self, invert_y: bool = False):
        """
        Args:
            invert_y: If true, inverts Y coordinates. Usually false for symbols
                      since EasyEDA and LibrePCB both use Y-up for symbols.
        """
        self.invert_y = invert_y
        self.grid_size = 2.54

    def _transform_y(self, y: float) -> float:
        return -y if self.invert_y else y

    def _transform_point(self, point: Point) -> List:
        return [point.x, self._transform_y(point.y)]

    def _map_pin_direction_to_rotation(self, direction: PinDirection) -> float:
        """Map CDM pin direction to LibrePCB rotation angle."""
        direction_to_rotation = {
            PinDirection.RIGHT: 180.0,  # Pin points right
            PinDirection.DOWN: 270.0,  # Pin points down
            PinDirection.LEFT: 0.0,  # Pin points left
            PinDirection.UP: 90.0,  # Pin points up
        }
        return direction_to_rotation.get(direction, 0.0)

    def _create_symbol_outline(self, symbol: Symbol) -> List[Tuple]:
        """Create a standard rectangular symbol outline based on symbol.width and symbol.height."""

        min_x = floor(min(p.position.x for p in symbol.pins))
        max_x = floor(max(p.position.x for p in symbol.pins))

        min_y = floor(min(p.position.y for p in symbol.pins))
        max_y = floor(max(p.position.y for p in symbol.pins))

        # if it's a vertical rectangle with pins on the left and right, this works.

        outline_vertices = [
            Point(x=(min_x + 1) * self.grid_size, y=(max_y + 1) * self.grid_size),
            Point(x=(max_x - 1) * self.grid_size, y=(max_y + 1) * self.grid_size),
            Point(x=(max_x - 1) * self.grid_size, y=(min_y - 1) * self.grid_size),
            Point(x=(min_x + 1) * self.grid_size, y=(min_y - 1) * self.grid_size),
            Point(x=(min_x + 1) * self.grid_size, y=(max_y + 1) * self.grid_size),
        ]

        return [
            (
                "polygon",
                [
                    uuid_module.uuid4(),
                    ("layer", [SExpSymbol("sym_outlines")]),
                    ("width", [0.2]),  # Standard outline stroke width
                    ("fill", [False]),
                    ("grab_area", [True]),
                ]
                + [
                    # Ensure these vertex positions are also snapped if transform_point doesn't do it
                    (
                        "vertex",
                        [("position", self._transform_point(vertex)), ("angle", [0.0])],
                    )
                    for vertex in outline_vertices
                ],
            )
        ]

    def _serialize_pins(self, symbol: Symbol) -> List[Tuple]:
        """Serialize symbol pins to LibrePCB format, ensuring grid alignment."""
        pin_tuples = []

        for pin in symbol.pins:
            rotation = self._map_pin_direction_to_rotation(pin.direction)
            name_align = [SExpSymbol("left"), SExpSymbol("center")]
            name_offset_x = self.grid_size * 1.25  # Name inside the symbol body
            name_offset_y = 0.0

            # Final pin position for S-expression, ensuring it's from pre-snapped values
            pin_final_x = floor(pin.position.x) * self.grid_size
            pin_final_y = self._transform_y(floor(pin.position.y) * self.grid_size)

            pin_tuple = (
                "pin",
                [
                    pin.uuid,
                    ("name", [pin.name]),
                    (
                        "position",
                        [pin_final_x, pin_final_y],
                    ),  # Use explicitly snapped values
                    ("rotation", [rotation]),
                    (
                        "length",
                        [self.grid_size],
                    ),  # Pin extends one grid unit from its position
                    ("name_position", [name_offset_x, name_offset_y]),
                    ("name_rotation", [0.0]),
                    (
                        "name_height",
                        [self.grid_size * 0.7],
                    ),  # Text height slightly smaller than grid
                    ("name_align", name_align),
                ],
            )
            pin_tuples.append(pin_tuple)
        return pin_tuples

    def _add_name_value_labels(self, symbol: Symbol) -> List[Tuple]:
        """Add standard {{NAME}} and {{VALUE}} text labels."""
        # Position labels relative to symbol body extents
        text_height = self.grid_size * 0.7

        min_x = floor(min(p.position.x for p in symbol.pins))
        min_y = floor(min(p.position.y for p in symbol.pins))
        max_y = floor(max(p.position.y for p in symbol.pins))

        name_pos_y = (max_y + 1) * self.grid_size
        value_pos_y = (min_y - 1) * self.grid_size

        # Center the labels horizontally
        label_x_pos = (min_x + 2) * self.grid_size

        return [
            (
                "text",
                [
                    uuid_module.uuid4(),
                    ("layer", [SExpSymbol("sym_names")]),
                    ("value", ["{{NAME}}"]),
                    (
                        "align",
                        [SExpSymbol("left"), SExpSymbol("bottom")],
                    ),  # Center aligned
                    ("height", [text_height]),
                    ("position", [label_x_pos, name_pos_y]),
                    ("rotation", [0.0]),
                ],
            ),
            (
                "text",
                [
                    uuid_module.uuid4(),
                    ("layer", [SExpSymbol("sym_values")]),
                    ("value", ["{{VALUE}}"]),
                    (
                        "align",
                        [SExpSymbol("left"), SExpSymbol("top")],
                    ),  # Center aligned
                    ("height", [text_height]),
                    ("position", [label_x_pos, value_pos_y]),
                    ("rotation", [0.0]),
                ],
            ),
        ]

    def _consolidate_duplicate_pins(self, symbol: Symbol) -> Symbol:
        """Consolidate duplicate pin names into single pins, following LibrePCB best practices."""
        unique_pins = {}
        consolidated_pins = []

        for pin in symbol.pins:
            pin_name = pin.name

            if pin_name in unique_pins:
                # Pin name already exists, skip this duplicate
                # In LibrePCB, multiple physical pins with same function
                # are handled in the device editor, not the symbol
                print(f"  Consolidating duplicate pin: {pin_name}")
                continue
            else:
                # First occurrence of this pin name, keep it
                unique_pins[pin_name] = pin
                consolidated_pins.append(pin)

        symbol.pins = consolidated_pins
        return symbol

    def serialize_to_file(
        self, symbol: Symbol, dir_path: str, filename: str = "symbol.lp"
    ):
        """Serialize Symbol to LibrePCB .sym file."""
        original_pin_count = len(symbol.pins)
        symbol = self._consolidate_duplicate_pins(symbol)
        final_pin_count = len(symbol.pins)

        symbol_contents = (
            [
                symbol.uuid,
                ("name", [symbol.name]),
                ("description", [symbol.description or ""]),
                ("keywords", [", ".join(symbol.keywords) if symbol.keywords else ""]),
                ("author", [symbol.author or "EasyEDA Converter"]),
                ("version", [symbol.version_str or const.DEFAULT_VERSION]),
                ("created", [symbol.created_at or datetime.now()]),
                ("deprecated", [False]),
                (
                    "generated_by",
                    [symbol.generated_by or "EasyEDA to LibrePCB Converter"],
                ),
                (  # Default "Unsorted" category UUID
                    "category",
                    [uuid_module.UUID("e29f0cb3-ef6d-4203-b854-d75150cbae0b")],
                ),
            ]
            + self._serialize_pins(symbol)
            + self._create_symbol_outline(symbol)
            + self._add_name_value_labels(symbol)
        )
        sexpr = serialize_to_sexpr("librepcb_symbol", symbol_contents)
        filepath = os.path.join(dir_path, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(sexpr)
        dotfilepath = os.path.join(dir_path, ".librepcb-sym")
        with open(dotfilepath, "w", encoding="utf-8") as f:
            f.write("1\n")
        duplicates_removed = original_pin_count - final_pin_count
        print(f"Symbol '{symbol.name}' serialized to LibrePCB symbol: {filepath}")
        print(
            f"  - {final_pin_count} unique pins (removed {duplicates_removed} duplicates)"
        )
        print("  - Arranged pins on 2.54mm grid")
        print(
            f"  - Symbol dimensions (body): {symbol.width:.2f} x {symbol.height:.2f} mm"
        )
