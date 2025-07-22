import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from librepcb_parts_generator.entities.common import (
    Author,
    Category,
    Created,
    Deprecated,
    Description,
    GeneratedBy,
    Keywords,
    Name,
    Position,
    Resource,
    Rotation,
    StringValue,
    Version,
)
from librepcb_parts_generator.entities.component import (
    Clock,
    Component,
    DefaultValue,
    ForcedNet,
    Gate,
    Negated,
    PinSignalMap,
    Prefix,
    Required,
    Role,
    SchematicOnly,
    Signal,
    SignalUUID,
    Suffix,
    SymbolUUID,
    TextDesignator,
)
from librepcb_parts_generator.entities.component import Variant as ComponentVariant
from librepcb_parts_generator.entities.package import Package
from librepcb_parts_generator.entities.symbol import Symbol as LibrepcbSymbol

from models.library_part import LibraryPart

logger = logging.getLogger(__name__)


def process_component_complete(
    library_part: LibraryPart,
    package: Package,
    symbol: LibrepcbSymbol,
) -> Optional[Component]:
    """
    Generate a LibrePCB component from a Package and a Symbol,
    preserving the ordinal pin mapping.
    """
    logger.info("--- Starting Component Generation ---")
    comp_dir = library_part.component.dir_path
    comp_uuid_str = library_part.component.uuid
    logger.info(f"Component UUID: {comp_uuid_str}")

    try:
        # Create Component
        component = Component(
            uuid=comp_uuid_str,
            name=Name(library_part.part_name),
            description=Description(library_part.full_description or ""),
            keywords=Keywords(""),
            author=Author("webparts-librepcb"),
            version=Version("0.1.0"),
            created=Created(datetime.now()),
            deprecated=Deprecated(False),
            generated_by=GeneratedBy(f"webparts:lcsc:{library_part.lcsc_id}"),
            categories=[Category("e29f0cb3-ef6d-4203-b854-d75150cbae0b")],
            schematic_only=SchematicOnly(False),
            default_value=DefaultValue("{{MPN or DEVICE or COMPONENT}}"),
            prefix=Prefix("U"),
        )

        # Create a default gate that uses the provided symbol
        gate = Gate(
            uuid=str(uuid.uuid4()),
            symbol_uuid=SymbolUUID(symbol.uuid),
            position=Position(0, 0),
            rotation=Rotation(0),
            required=Required(True),
            suffix=Suffix(""),
        )

        # Iterate through the symbol's pins IN THEIR ORIGINAL, PARSED ORDER.
        for pin in symbol.pins:
            # 1. Create a logical signal for the component, using a random UUID.
            signal = Signal(
                uuid=str(uuid.uuid4()),
                name=pin.name,
                role=Role(Role.PASSIVE),
                required=Required(False),
                negated=Negated(False),
                clock=Clock(False),
                forced_net=ForcedNet(""),
            )
            component.add_signal(signal)

            # 2. Create the pin-to-signal mapping.
            #
            #    CRITICAL: Reuse the original symbol pin's UUID for the mapping.
            #    This creates a direct, unambiguous link between the gate pin
            #    and the symbol pin, which is the robust, official method.
            pin_signal_map = PinSignalMap(
                pin_uuid=pin.uuid,  # <-- Use the symbol's actual pin UUID
                signal_uuid=SignalUUID(signal.uuid),
                text_designator=TextDesignator(TextDesignator.SIGNAL_NAME),
            )
            gate.add_pin_signal_map(pin_signal_map)

        # Create a default variant and add the gate
        variant = ComponentVariant(
            uuid=str(uuid.uuid4()),
            norm=StringValue("norm", ""),
            name=Name("default"),
            description=Description(""),
            gate=gate,
        )
        component.add_variant(variant)

        # Serialize component
        parent_dir = Path(*Path(comp_dir).parts[0:-1])
        component.serialize(parent_dir)
        logger.info(f"Successfully generated component '{component.name.value}'.")
        return component

    except KeyboardInterrupt:
        logger.info(
            "\nProcess interrupted by user during component generation. Exiting."
        )
        raise
    except Exception as e:
        logger.error(
            f"An error occurred during component generation: {e}", exc_info=True
        )
        return None
