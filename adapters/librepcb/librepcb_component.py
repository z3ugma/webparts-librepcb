# librepcb_serializer.py

# Global imports
import logging
import os
import uuid as uuid_module  # To avoid conflict with our Pydantic UUID
from datetime import datetime
from typing import List, Tuple

import constants as const
from models.symbol import Symbol

# Local imports
from .librepcb_uuid import create_derived_uuidv4
from .s_expression import SExpSymbol, serialize_to_sexpr
from models.elements import LibrePCBElement

logger = logging.getLogger(__name__)


class LibrePCBComponentSerializer:
    def serialize(
        self, symbol: Symbol, component_uuid: str, component_name: str
    ) -> str:
        """
        Serialize a Symbol to a LibrePCB component S-expression string.

        Args:
            symbol: The Symbol object to serialize
            component_uuid: The UUID for the component
            component_name: The name for the component

        Returns:
            A LibrePCB component S-expression string
        """
        # Consolidate duplicate pins first
        original_pin_count = len(symbol.pins)
        symbol = self._consolidate_duplicate_pins(symbol)
        final_pin_count = len(symbol.pins)

        if original_pin_count != final_pin_count:
            logger.info(
                f"Consolidated {original_pin_count - final_pin_count} duplicate pins in {symbol.name}"
            )

        # Build the component S-expression
        component_contents = (
            [
                component_uuid,
                ("name", [component_name]),
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
                (
                    "category",
                    [uuid_module.UUID("e29f0cb3-ef6d-4203-b854-d75150cbae0b")],
                ),  # Default "Unsorted" category
                ("schematic_only", [False]),
                ("default_value", ["{{MPN or DEVICE}}"]),
                ("prefix", [symbol.prefix or ""]),
            ]
            + self._serialize_signals(symbol)
            + self._serialize_variant(symbol)
        )

        return serialize_to_sexpr("librepcb_component", component_contents)

    def _serialize_signals(self, symbol: Symbol) -> List[Tuple]:
        """Serialize symbol pins to LibrePCB format, ensuring grid alignment."""
        pin_tuples = []

        for pin in symbol.pins:
            pin_tuple = (
                "signal",
                [
                    create_derived_uuidv4(pin.uuid, pin.name),
                    ("name", [pin.name]),
                    (
                        "role",
                        [SExpSymbol("passive")],
                    ),
                    ("required", [False]),
                    (
                        "negated",
                        [False],
                    ),
                    ("clock", [False]),
                    ("forced_net", ["GND" if pin.name == "GND" else ""]),
                ],
            )
            pin_tuples.append(pin_tuple)
        return pin_tuples

    def _consolidate_duplicate_pins(self, symbol: Symbol) -> Symbol:
        """Consolidate duplicate pin names into single pins, following LibrePCB best practices."""
        unique_pins = {}
        consolidated_pins = []

        for pin in symbol.pins:
            pin_name = pin.name

            if pin_name in unique_pins:
                # Pin name already exists, skip this duplicate
                print(f"  Consolidating duplicate pin: {pin_name}")
                continue
            else:
                # First occurrence of this pin name, keep it
                unique_pins[pin_name] = pin
                consolidated_pins.append(pin)

        symbol.pins = consolidated_pins
        return symbol

    def _serialize_variant(self, symbol: Symbol) -> List[Tuple]:
        return [
            (
                "variant",
                [
                    uuid_module.uuid4(),
                    ("norm", [""]),
                    ("name", ["default"]),
                    ("description", [""]),
                    (
                        "gate",
                        [
                            uuid_module.uuid4(),
                            ("symbol", [symbol.uuid]),
                            ("position", [0.0, 0.0]),
                            ("rotation", [0.0]),
                            ("required", [True]),
                            ("suffix", [""]),
                        ]
                        + [
                            (
                                "pin",
                                [
                                    pin.uuid,
                                    (
                                        "signal",
                                        [create_derived_uuidv4(pin.uuid, pin.name)],
                                    ),
                                    ("text", [SExpSymbol("signal")]),
                                ],
                            )
                            for pin in symbol.pins
                        ],
                    ),
                ],
            )
        ]

    def serialize_to_file(
        self,
        symbol: Symbol,
        dir_path: str,
        component_uuid: str = None,
        component_name: str = None,
        filename: str = LibrePCBElement.COMPONENT.filename,
    ):
        """Serialize Symbol as a Component to LibrePCB .cmp file."""
        # Use provided values or derive from symbol
        if component_uuid is None:
            component_uuid = create_derived_uuidv4(symbol.uuid, "component")
        if component_name is None:
            component_name = symbol.name

        # Generate the S-expression content
        sexpr = self.serialize(symbol, component_uuid, component_name)

        # Write to file
        filepath = os.path.join(dir_path, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(sexpr)

        # Create the .librepcb-cmp marker file
        dotfilepath = os.path.join(dir_path, ".librepcb-cmp")
        with open(dotfilepath, "w", encoding="utf-8") as f:
            f.write("1\n")

        logger.info(
            f"Component '{component_name}' serialized to LibrePCB component: {filepath}"
        )
        return filepath
