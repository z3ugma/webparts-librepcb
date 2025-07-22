import logging
from datetime import datetime
from pathlib import Path

from librepcb_parts_generator.entities.common import (
    Author,
    Category,
    Created,
    Deprecated,
    Description,
    GeneratedBy,
    Keywords,
    Name,
    Resource,
    Version,
)
from librepcb_parts_generator.entities.component import Component
from librepcb_parts_generator.entities.device import (
    ComponentPad,
    ComponentUUID,
    Device,
    Manufacturer,
    PackageUUID,
    Part,
    SignalUUID,
)
from librepcb_parts_generator.entities.package import Package

from models.library_part import LibraryPart
from models.pin_mapping import PinMapping

logger = logging.getLogger(__name__)


def process_device_complete(
    library_part: LibraryPart,
    package: Package,
    component: Component,
    pin_mapping: PinMapping,
) -> bool:
    """
    Generate a LibrePCB device, mapping all unconsolidated pins to pads.
    """
    logger.info("--- Starting Device Generation ---")
    dev_dir = library_part.device.dir_path
    dev_uuid = library_part.device.uuid

    try:
        # Create Device
        device = Device(
            uuid=dev_uuid,
            name=Name(library_part.part_name),
            description=Description(library_part.full_description or ""),
            keywords=Keywords(""),
            author=Author("webparts-librepcb"),
            version=Version("0.1.0"),
            created=Created(datetime.now()),
            deprecated=Deprecated(False),
            generated_by=GeneratedBy(f"webparts:lcsc:{library_part.lcsc_id}"),
            categories=[Category("e29f0cb3-ef6d-4203-b854-d75150cbae0b")],
            component_uuid=ComponentUUID(component.uuid),
            package_uuid=PackageUUID(package.uuid),
        )
        # Add the manufacturer part number (MPN) to the device
        part = Part(
            mpn=library_part.mfr_part_number,
            manufacturer=Manufacturer(library_part.manufacturer),
        )
        device.add_part(part)
        device.add_resource(
            Resource(
                name="Datasheet",
                mediatype="application/pdf",
                url=library_part.datasheet_url,
            )
        )

        # Map component signals to package pads
        default_footprint = next(
            (fp for fp in package.footprints if fp.name.value == "default"), None
        )
        if not default_footprint:
            logger.error("Default footprint 'default' not found in package.")
            return False

        # Create lookups for faster access
        package_pads_by_uuid = {pad.uuid: pad for pad in package.pads}
        signals_by_name = {signal.name.value: signal for signal in component.signals}

        # Create a lookup for footprint pads by their number (name)
        pads_by_number = {}
        for fp_pad in default_footprint.pads:
            pkg_pad = package_pads_by_uuid.get(fp_pad.package_pad.uuid)
            if pkg_pad:
                pads_by_number[pkg_pad.name.value] = fp_pad

        # Iterate through the full pin mapping
        for pin_name, pin_number, _ in pin_mapping.pins:
            signal = signals_by_name.get(pin_name)
            pad = pads_by_number.get(pin_number)

            if signal and pad:
                package_pad_uuid = pad.package_pad.uuid
                component_pad = ComponentPad(
                    pad_uuid=package_pad_uuid, signal=SignalUUID(signal.uuid)
                )
                device.add_pad(component_pad)
                logger.debug(f"Mapped signal '{pin_name}' to pad '{pin_number}'.")
            else:
                if not signal:
                    logger.warning(f"Could not find signal for pin name '{pin_name}'.")
                if not pad:
                    logger.warning(f"Could not find pad for pin number '{pin_number}'.")

        # Serialize device
        parent_dir = Path(*Path(dev_dir).parts[0:-1])
        device.serialize(parent_dir)
        logger.info(f"Successfully generated device '{device.name.value}'.")
        return True

    except KeyboardInterrupt:
        logger.info("\nProcess interrupted by user during device generation. Exiting.")
        raise
    except Exception as e:
        logger.error(f"An error occurred during device generation: {e}", exc_info=True)
        return False
