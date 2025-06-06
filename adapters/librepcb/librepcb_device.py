# librepcb_serializer.py

# Global imports
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


class LibrePCBDeviceSerializer:
    def _serialize_signals(self, symbol: Symbol, footprint: Footprint) -> List[Tuple]:
        pin_tuples = []

        for pad in footprint.pads:
            corresponding_pins = [
                pin for pin in symbol.pins if pin.number == pad.number
            ]
            pin = first(corresponding_pins)

            if not pin:
                print(
                    f"\t - WARNING! Pad {pad.number} without corresponding Pin (removed duplicate)"
                )
                pin_tuple = (
                    "pad",
                    [pad.uuid, ("signal", [SExpSymbol("none")])],
                )

                # TODO - we need to figure out a way to not consolidate pins, for Device purposes.
                # Map pads with duplicate names/nets to the one pin that survives after consolidating duplicates
                # Could not add device:
                # Package pad "01129e74-5ca8-4fee-99c2-b9e429701324" not found in pad-signal-map of device "a32088c9-ef07-4d14-89e4-ef39c5bac4f3".
            else:
                # (pad 05a64b16-8324-45a7-a71d-687946713c28 (signal 1a85a560-fac6-486e-862d-8f57464ffa0a))
                #  (pad 186b0e49-aef9-40c1-9a24-85b2e65379a7 (signal 0b9685c5-4cce-4358-a92c-15c9fc97fc4d))
                #  (pad 2a3f2101-d2e9-48c5-a181-522b8f87f677 (signal 0b9685c5-4cce-4358-a92c-15c9fc97fc4d))

                pin_tuple = (
                    "pad",
                    [pad.uuid, ("signal", [create_derived_uuidv4(pin.uuid, pin.name)])],
                )
            pin_tuples.append(pin_tuple)
        return pin_tuples

    # def _consolidate_duplicate_pins(self, symbol: Symbol) -> Symbol:
    #     """Consolidate duplicate pin names into single pins, following LibrePCB best practices."""
    #     unique_pins = {}
    #     consolidated_pins = []

    #     for pin in symbol.pins:
    #         pin_name = pin.name

    #         if pin_name in unique_pins:
    #             # Pin name already exists, skip this duplicate
    #             # In LibrePCB, multiple physical pins with same function
    #             # are handled in the device editor, not the symbol
    #             print(f"  Consolidating duplicate pin: {pin_name}")
    #             continue
    #         else:
    #             # First occurrence of this pin name, keep it
    #             unique_pins[pin_name] = pin
    #             consolidated_pins.append(pin)

    #     symbol.pins = consolidated_pins
    #     return symbol

    def serialize_to_file(
        self,
        symbol: Symbol,
        footprint: Footprint,
        dir_path: str,
        filename: str = "device.lp",
    ):
        """Serialize Symbol as a Component to LibrePCB .cmp file."""
        # original_pin_count = len(symbol.pins)
        # symbol = self._consolidate_duplicate_pins(symbol)
        # final_pin_count = len(symbol.pins)

        # (librepcb_device 3c65d5d1-0305-48c1-a3a3-aabf27faf7bb
        #  (name "10118193-0001LF")
        #  (description "")
        #  (keywords "eagle,import")
        #  (author "EAGLE Import")
        #  (version "0.1")
        #  (created 2024-12-29T22:34:03Z)
        #  (deprecated false)
        #  (generated_by "EagleImport::::10118193-0001LF::")
        #  (category d0618c29-0436-42da-a388-fdadf7b23892)
        #  (component 68ec2ee6-08e1-4d20-864f-5b9a29a0e5e2)
        #  (package faeb7a92-fb56-4ae5-ae1d-98dcf0837a89)
        #  (part "ESP32-C6" (manufacturer "Espressif")
        #  (pad 05a64b16-8324-45a7-a71d-687946713c28 (signal 1a85a560-fac6-486e-862d-8f57464ffa0a))
        #  (pad 186b0e49-aef9-40c1-9a24-85b2e65379a7 (signal 0b9685c5-4cce-4358-a92c-15c9fc97fc4d))
        #  (pad 2a3f2101-d2e9-48c5-a181-522b8f87f677 (signal 0b9685c5-4cce-4358-a92c-15c9fc97fc4d))
        #  (pad 6c3cdcbe-6114-4eaf-859f-9a6bd7c088c5 (signal eecadf03-fc2d-492d-8731-83bb0d265190))
        #  (pad 7f822861-bbc8-4483-9105-3248968e23cb (signal de62b467-4058-4b2e-862d-79cdf5a5212d))
        #  (pad 9403f4c3-85e0-4b3b-a0b1-3871ef6b73eb (signal 648d9613-0cef-4263-b47b-e1c6c5ff5998))
        #  (pad 9e5b5c92-bb8c-4099-a0b8-7b9e3a4ce739 (signal 0b9685c5-4cce-4358-a92c-15c9fc97fc4d))
        #  (pad c59cfe05-238e-4a82-8983-eeb7475a4f12 (signal 0b9685c5-4cce-4358-a92c-15c9fc97fc4d))
        #  (pad da9e80f1-10dd-48bd-8f99-3511f4a7326d (signal 0b9685c5-4cce-4358-a92c-15c9fc97fc4d))
        #  (pad f1b16454-ac71-453d-bb88-fb90a34128c9 (signal 52cd7fe9-1b3e-4984-b966-81f8734adf59))
        #  (pad fa479759-c9dc-40d5-a229-252c990aa7e6 (signal 0b9685c5-4cce-4358-a92c-15c9fc97fc4d))
        # )

        device_contents = [
            create_derived_uuidv4(symbol.uuid, "device"),
            ("name", [symbol.name]),
            ("description", [symbol.description or ""]),
            ("keywords", [", ".join(symbol.keywords) if symbol.keywords else ""]),
            ("author", [symbol.author or "EasyEDA Converter"]),
            ("version", [symbol.version_str or "0.1"]),
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
            ("component", [create_derived_uuidv4(symbol.uuid, "component")]),
            ("package", [footprint.uuid]),
        ] + self._serialize_signals(symbol, footprint)

        sexpr = serialize_to_sexpr("librepcb_device", device_contents)
        filepath = os.path.join(dir_path, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(sexpr)
        dotfilepath = os.path.join(dir_path, ".librepcb-dev")
        with open(dotfilepath, "w", encoding="utf-8") as f:
            f.write("1\n")
        # duplicates_removed = original_pin_count - final_pin_count
        print(f"Device '{symbol.name}' serialized to LibrePCB component: {filepath}")
