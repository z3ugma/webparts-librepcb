# main.py

# Global imports
import json
import os  # For path joining
import shutil
from typing import Optional

from adapters.easyeda.easyeda_footprint import EasyEDAParser
from adapters.easyeda.easyeda_symbol import EasyEDASymbolParser
from adapters.librepcb.librepcb_component import LibrePCBComponentSerializer
from adapters.librepcb.librepcb_device import LibrePCBDeviceSerializer
from adapters.librepcb.librepcb_footprint import LibrePCBFootprintSerializer
from adapters.librepcb.librepcb_symbol import LibrePCBSymbolSerializer
from adapters.librepcb.librepcb_uuid import create_derived_uuidv4
from models.footprint import Footprint
from models.symbol import Symbol

# --- Load EasyEDA JSON ---

id = "C5364646"
try:
    # Adjust path if your JSON is elsewhere or you want it configurable
    with open(f"downloads/{id}.json", "r", encoding="utf-8") as f:
        easyeda_json_data = json.load(f)
except FileNotFoundError:
    print(f"Error: {id}.json not found.")
    exit(1)
except json.JSONDecodeError:
    print(f"Error: {id}.json is not a valid JSON file.")
    exit(1)


# Check if this has both symbol and footprint data
has_symbol = "dataStr" in easyeda_json_data and easyeda_json_data["dataStr"]
has_footprint = (
    "packageDetail" in easyeda_json_data and easyeda_json_data["packageDetail"]
)

has_3d = False


if has_symbol:
    print("\n=== Symbol Data Structure ===")
    symbol_data = easyeda_json_data["dataStr"]
    if "shape" in symbol_data:
        print(f"Symbol shapes count: {len(symbol_data['shape'])}")

if has_footprint:
    print("\n=== Footprint Data Structure ===")
    footprint_data = easyeda_json_data["packageDetail"]["dataStr"]
    if "shape" in footprint_data:
        print(f"Footprint shapes count: {len(footprint_data['shape'])}")

        svgnodes = [k for k in footprint_data["shape"] if k.startswith("SVGNODE")]
        if svgnodes:
            has_3d = True
            print("\n=== 3D STEP Model ===")

# --- Parse Symbol if available ---
canonical_symbol: Optional[Symbol] = None
if has_symbol:
    print("\n=== Parsing Symbol ===")
    try:
        symbol_parser = EasyEDASymbolParser()
        canonical_symbol = symbol_parser.parse_easyeda_symbol(easyeda_json_data)

        if canonical_symbol:
            print("\n--- Canonical Symbol (Parsed from EasyEDA) ---")
            canonical_symbol.pretty_print()
        else:
            print("Failed to parse symbol data.")
    except Exception as e:
        print(f"Error parsing symbol: {e}")
        # Global imports
        import traceback

        traceback.print_exc()

# --- Parse Footprint if available ---
canonical_footprint: Optional[Footprint] = None
if has_footprint:
    print("\n=== Parsing Footprint ===")
    try:
        easyeda_parser = EasyEDAParser()
        canonical_footprint = easyeda_parser.parse_easyeda_json(easyeda_json_data)

        if canonical_footprint:
            print("\n--- Canonical Footprint (Parsed from EasyEDA) ---")
            canonical_footprint.pretty_print()
        else:
            print("Failed to parse footprint data.")
    except Exception as e:
        print(f"Error parsing footprint: {e}")
        # Global imports
        import traceback

        traceback.print_exc()

# --- Serialize to LibrePCB if we have data ---
if canonical_footprint:
    print("\n=== Serializing Footprint to LibrePCB ===")
    try:
        librepcb_serializer = LibrePCBFootprintSerializer(invert_y=True)
        output_dir = f"/Users/fred/LibrePCB-Workspace/data/libraries/local/EasyEDA.lplib/pkg/{canonical_footprint.uuid}"
        os.makedirs(output_dir, exist_ok=True)
        librepcb_serializer.serialize_to_file(canonical_footprint, output_dir)
        if has_3d:
            shutil.copy(
                f"./downloads/{id}.step",
                output_dir + f"/{canonical_footprint.model_3d.uuid}.step",
            )
    except Exception as e:
        print(f"Error during LibrePCB footprint serialization: {e}")
        # Global imports
        import traceback

        traceback.print_exc()
# Add this debug code to main.py after the symbol parsing section:

if canonical_symbol:
    print("\n=== Debug: Raw EasyEDA Symbol Data ===")
    symbol_data = easyeda_json_data["dataStr"]

    # Look at the shapes
    print(f"Total shapes in EasyEDA data: {len(symbol_data.get('shape', []))}")

    # Show first few shapes to understand the format
    for i, shape in enumerate(symbol_data.get("shape", [])[:5]):
        shape_type = shape.split("~")[0] if "~" in shape else "unknown"
        print(f"Shape {i}: Type={shape_type}")
        if shape_type == "P":  # Pin
            print(f"  Pin data: {shape[:100]}...")
        elif shape_type == "R":  # Rectangle
            print(f"  Rect data: {shape}")
        else:
            print(f"  Data: {shape}")

    # Check if there are more graphics we're missing
    non_pin_shapes = [s for s in symbol_data.get("shape", []) if not s.startswith("P~")]
    print(f"\nNon-pin shapes: {len(non_pin_shapes)}")
    for shape in non_pin_shapes:
        shape_type = shape.split("~")[0] if "~" in shape else "unknown"
        print(f"  {shape_type}: {shape}")
        # Add after the debug code above:

    if symbol_data.get("shape"):
        first_pin = next((s for s in symbol_data["shape"] if s.startswith("P~")), None)
        if first_pin:
            print("\nFirst pin raw data:")
            print(first_pin)
            print("\nPin segments (split by ^^):")
            segments = first_pin.split("^^")
            for i, segment in enumerate(segments):
                print(f"  [{i}]: {segment}")
    canonical_symbol.pretty_print()
    print("\n=== Serializing Symbol to LibrePCB ===")
    try:
        symbol_serializer = LibrePCBSymbolSerializer(
            invert_y=True
        )  # Symbols typically don't need Y inversion
        output_dir = f"/Users/fred/LibrePCB-Workspace/data/libraries/local/EasyEDA.lplib/sym/{canonical_symbol.uuid}"
        os.makedirs(output_dir, exist_ok=True)
        symbol_serializer.serialize_to_file(canonical_symbol, output_dir)
    except Exception as e:
        print(f"Error during LibrePCB symbol serialization: {e}")
        # Global imports
        import traceback

        traceback.print_exc()

if canonical_symbol and canonical_footprint:
    # This means that we have enough to make a whole Device in LibrePCB.
    # Starting with the Component
    print("\n=== Serializing Component to LibrePCB ===")
    try:
        component_serializer = LibrePCBComponentSerializer()
        new_uuid = create_derived_uuidv4(canonical_symbol.uuid, "component")
        output_dir = f"/Users/fred/LibrePCB-Workspace/data/libraries/local/EasyEDA.lplib/cmp/{new_uuid}"
        os.makedirs(output_dir, exist_ok=True)
        component_serializer.serialize_to_file(canonical_symbol, output_dir)
    except Exception as e:
        print(f"Error during LibrePCB component serialization: {e}")
        # Global imports
        import traceback

        traceback.print_exc()

    # Then the Device
    print("\n=== Serializing Device to LibrePCB ===")
    try:
        device_serializer = LibrePCBDeviceSerializer()
        new_uuid = create_derived_uuidv4(canonical_symbol.uuid, "device")
        output_dir = f"/Users/fred/LibrePCB-Workspace/data/libraries/local/EasyEDA.lplib/dev/{new_uuid}"
        os.makedirs(output_dir, exist_ok=True)
        device_serializer.serialize_to_file(
            canonical_symbol, canonical_footprint, output_dir
        )
    except Exception as e:
        print(f"Error during LibrePCB device serialization: {e}")
        # Global imports
        import traceback

        traceback.print_exc()
