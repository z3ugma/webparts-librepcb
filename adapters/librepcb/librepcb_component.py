# librepcb_serializer.py

# Global imports
import os
import uuid as uuid_module  # To avoid conflict with our Pydantic UUID
from datetime import datetime
from typing import List, Tuple

from models.symbol import Symbol

# Local imports
from .librepcb_uuid import create_derived_uuidv4
from .s_expression import SExpSymbol, serialize_to_sexpr

import constants as const


class LibrePCBComponentSerializer:
    def _serialize_signals(self, symbol: Symbol) -> List[Tuple]:
        """Serialize symbol pins to LibrePCB format, ensuring grid alignment."""
        pin_tuples = []

        for pin in symbol.pins:
            #  (signal c8f03397-69d8-4d01-b620-6fee41ce6771 (name "C_SW1") (role passive)
            #   (required true) (negated false) (clock false) (forced_net "")
            #  )
            #  (signal b2156d45-0554-45dc-8520-31de8ddb6b99 (name "STAR_SW2") (role passive)
            #   (required true) (negated false) (clock false) (forced_net "")
            #  )
            #  (signal 697285c5-b531-488e-8ee2-5ae6e9628faf (name "W_SW1") (role passive)
            #   (required true) (negated false) (clock false) (forced_net "")
            #  )
            #  (signal db1dcb31-20c1-4bb1-9dc5-20cea994f70b (name "RH_SW1") (role passive)
            #   (required true) (negated false) (clock false) (forced_net "")
            #  )
            #
            #  (variant 50e5db72-6818-4eb1-85c4-d76c65833d83 (norm "")
            #   (name "default")
            #   (description "")
            #   (gate afa58c91-8339-4579-8351-5634f5b2e6be
            #    (symbol ada0f57f-2d6d-4d9a-b349-68adcf5ed8ad)
            #    (position 0.0 0.0) (rotation 0.0) (required true) (suffix "")
            #    (pin 0349286d-379d-473d-8776-46ffb25cfa5c (signal 3981e19c-b1d0-4716-99e1-460914215f9d) (text signal))
            #    (pin 08ea2f07-3d0b-451a-b8b1-37feb5341915 (signal 7f7edc74-18d7-471d-b4cb-3b77bb083f42) (text signal))
            #    (pin 108b5342-0fff-4000-89c0-74de253cf41b (signal f86d5228-0824-4692-b440-3973670c3c71) (text signal))
            #    (pin 10a03844-c0c4-4edf-804a-43e539569622 (signal 5fc0257a-6d39-4eed-ba0e-437ec8b77dcb) (text signal))
            #    (pin 2aec002d-e354-4d43-bc69-e77141599662 (signal 97115190-e55a-4fdf-bb4d-8b7693711562) (text signal))
            #   )
            #  )
            # )

            #  (signal c8f03397-69d8-4d01-b620-6fee41ce6771 (name "C_SW1") (role passive)
            #   (required true) (negated false) (clock false) (forced_net "")
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

    def _serialize_variant(self, symbol: Symbol) -> List[Tuple]:
        #  (variant 50e5db72-6818-4eb1-85c4-d76c65833d83 (norm "")
        #   (name "default")
        #   (description "")
        #   (gate afa58c91-8339-4579-8351-5634f5b2e6be
        #    (symbol ada0f57f-2d6d-4d9a-b349-68adcf5ed8ad)
        #    (position 0.0 0.0) (rotation 0.0) (required true) (suffix "")
        #    (pin 0349286d-379d-473d-8776-46ffb25cfa5c (signal 3981e19c-b1d0-4716-99e1-460914215f9d) (text signal))
        #   )
        #  )
        # )
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
        self, symbol: Symbol, dir_path: str, filename: str = "component.lp"
    ):
        """Serialize Symbol as a Component to LibrePCB .cmp file."""
        original_pin_count = len(symbol.pins)
        symbol = self._consolidate_duplicate_pins(symbol)
        final_pin_count = len(symbol.pins)

        symbol_contents = (
            [
                create_derived_uuidv4(symbol.uuid, "component"),
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
                ("schematic_only", [False]),
                ("default_value", ["{{MPN or DEVICE}}"]),
                ("prefix", [symbol.prefix[0] or ""]),
            ]
            + self._serialize_signals(symbol)
            + self._serialize_variant(symbol)
        )

        sexpr = serialize_to_sexpr("librepcb_component", symbol_contents)
        filepath = os.path.join(dir_path, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(sexpr)
        dotfilepath = os.path.join(dir_path, ".librepcb-cmp")
        with open(dotfilepath, "w", encoding="utf-8") as f:
            f.write("1\n")
        # duplicates_removed = original_pin_count - final_pin_count
        print(f"Component '{symbol.name}' serialized to LibrePCB component: {filepath}")
