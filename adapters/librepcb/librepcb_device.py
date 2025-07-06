# librepcb_serializer.py

# Global imports
import logging
import os
import uuid as uuid_module  # To avoid conflict with our Pydantic UUID
from datetime import datetime
from typing import List, Tuple

from first import first

from models.footprint import Footprint
from models.symbol import Symbol

# Local imports
from .librepcb_uuid import create_derived_uuidv4
from .s_expression import SExpSymbol, serialize_to_sexpr
import constants as const
from models.elements import LibrePCBElement

logger = logging.getLogger(__name__)


class LibrePCBDeviceSerializer:
    def serialize(
        self,
        symbol: Symbol,
        footprint: Footprint,
        device_uuid: str,
        device_name: str,
        component_uuid: str,
    ) -> str:
        """
        Serialize Symbol and Footprint to a LibrePCB device S-expression string.

        Args:
            symbol: The Symbol object to serialize
            footprint: The Footprint object to serialize
            device_uuid: The UUID for the device
            device_name: The name for the device
            component_uuid: The UUID of the associated component

        Returns:
            A LibrePCB device S-expression string
        """
        device_contents = [
            device_uuid,
            ("name", [device_name]),
            ("description", [symbol.description or ""]),
            ("keywords", [", ".join(symbol.keywords) if symbol.keywords else ""]),
            ("author", [symbol.author or "EasyEDA Converter"]),
            ("version", [symbol.version_str or const.DEFAULT_VERSION]),
            ("created", [symbol.created_at or datetime.now()]),
            ("deprecated", [False]),
            ("generated_by", [symbol.generated_by or "EasyEDA to LibrePCB Converter"]),
            (
                "category",
                [uuid_module.UUID("e29f0cb3-ef6d-4203-b854-d75150cbae0b")],
            ),  # Default "Unsorted" category
            ("component", [component_uuid]),
            ("package", [footprint.uuid]),
        ] + self._serialize_signals(symbol, footprint)

        return serialize_to_sexpr("librepcb_device", device_contents)

    def _serialize_signals(self, symbol: Symbol, footprint: Footprint) -> List[Tuple]:
        pin_tuples = []

        for pad in footprint.pads:
            corresponding_pins = [
                pin for pin in symbol.pins if pin.number == pad.number
            ]
            pin = first(corresponding_pins)

            if not pin:
                print(
                    f"	 - WARNING! Pad {pad.number} without corresponding Pin (removed duplicate)"
                )
                pin_tuple = (
                    "pad",
                    [pad.uuid, ("signal", [SExpSymbol("none")])],
                )
            else:
                pin_tuple = (
                    "pad",
                    [pad.uuid, ("signal", [create_derived_uuidv4(pin.uuid, pin.name)])],
                )
            pin_tuples.append(pin_tuple)
        return pin_tuples

    def serialize_to_file(
        self,
        symbol: Symbol,
        footprint: Footprint,
        dir_path: str,
        device_uuid: str = None,
        device_name: str = None,
        component_uuid: str = None,
        filename: str = LibrePCBElement.DEVICE.filename,
    ):
        """Serialize Symbol and Footprint as a Device to LibrePCB .dev file."""
        # Use provided values or derive from symbol
        if device_uuid is None:
            device_uuid = create_derived_uuidv4(symbol.uuid, "device")
        if device_name is None:
            device_name = symbol.name
        if component_uuid is None:
            component_uuid = create_derived_uuidv4(symbol.uuid, "component")

        # Generate the S-expression content
        sexpr = self.serialize(
            symbol, footprint, device_uuid, device_name, component_uuid
        )

        # Write to file
        filepath = os.path.join(dir_path, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(sexpr)

        # Create the .librepcb-dev marker file
        dotfilepath = os.path.join(dir_path, ".librepcb-dev")
        with open(dotfilepath, "w", encoding="utf-8") as f:
            f.write("1\n")

        logger.info(f"Device '{device_name}' serialized to LibrePCB device: {filepath}")
        return filepath
