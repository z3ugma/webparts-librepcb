# WebParts for LibrePCB

A search tool that finds datasheets, footprints, and schematics across different web EDA vendors and imports them into LibrePCB libraries

# Project Goals

The overall project goal is that a Web based library > search > copy to local > review footprints/schematics can be "the Library" workflow that solves a lot of the commentary about not enough components being available in the standard libraries of LibrePCB

Serve as a companion to LibrePCB to make finding parts easier.
In LibrePCB's forums and in GitHub issues, the opinion seems to be that there's no easy, automatic way to get a reliable online parts catalog.
Library conversion is hard, and professional PCB designers already usually have to review online-sourced footprints. Compounding the issue is that different EDAs and PCB design softwares follow different conventions for how they label things in a schematic.

# Vision

A PySide6 and Qt6 user interface written in Python and packaged as a single .exe/binary that searches online for electronic components and finds schematics, footprints, 3D models and datasheets.

Converts from different web EDA vendors' footprint languages into LibrePCB s-expressions primitives.
Inspired by https://github.com/uPesy/easyeda2kicad.py and https://github.com/dbrgn/svg2librepcb
Creates/finds a local library on the user's computer in the directory of their choosing and add "their" EasyEDA components searched in the UI to the local library

Desired web search endpoints:

- [EasyEDA](https://easyeda.com/) and [LCSC](https://www.lcsc.com/)
- SnapEDA
- Partstack
- Digikey
- Mouser

Once a part is found, WebParts gives you a workflow to review the accuracy of the symbols.
The addition of Footprint images in a recent LibrePCB release is a foundation for this review workflow

In the long term it would be nice to have this feature integrated in LibrePCB. There are at present 2 options for where the library search and conversions ought to be done:

1. _Locally_ like the existing Eagle/KiCad importers (then it should be written in Rust or C++)
2. _Server-Side_ on the LibrePCB API server: because it relies on API access of 3rd part web searches like EasyEDA which could theoretically break at any time. On the server, part search could be vendor-agnostic in the server API. Have a "LibrePCB parts search" that uses the API endpoint listed in Settings (so that if someone really wanted to roll another compatible API server they could) and extend the existing "parts" https://github.com/LibrePCB/librepcb-api-server/blob/master/app.py#L261 call to also be able to send footprints/symbols.

Then, the workflow UI tool is focused on search > results review > copy part into local library > review symbols for accuracy

# Future

An extension of this could be: after an individual reviews the footprint and "approves" it, then keep a count of "approved" footprints that gets sent back to the server for a "confidence score" of how good the part is in the server library.

See also [IDEAS.md](IDEAS.md)

# Usage

It is recommended to have [`uv`](https://docs.astral.sh/uv/) installed,
otherwise just run the scripts with `python` instead of `uv run` and
install dependencies manually.

## Downloading EasyEDA files

```bash
# To Download the relevant EasyEDA files
# Modify app.py with the LCSC ID of interest
and then run:
uv run app.py
2025-06-04 08:36:32,418 - adapters.easyeda.easyeda_api - INFO - 200 https://easyeda.com/api/products/{lcsc_id}/components?version=6.4.19.5
2025-06-04 08:36:32,726 - adapters.easyeda.easyeda_api - INFO - 200 https://modules.easyeda.com/qAxj6KHrDKw4blvCG8QJPs7Y/{uuid}
Found 3D Model STEP file, saving...
2025-06-04 08:36:32,960 - adapters.easyeda.easyeda_api - INFO - 200 https://easyeda.com/api/products/{lcsc_id}/svgs
2025-06-04 08:36:32,967 - svg_add_pad_labels - INFO - Created <g id='pcbPadNumbers'>
2025-06-04 08:36:32,967 - svg_add_pad_labels - INFO - Processed 57 pad elements.
2025-06-04 08:36:32,975 - svg_add_pad_labels - INFO - Successfully wrote modified SVG to 'downloads/C2040_1.svg.text.svg'

downloads % tree
.
├── C2040_0.svg
├── C2040_1.svg
├── C2040_1.svg.text.svg
├── C2040_svgs.json
├── C2040.json
```

## Converting to LibrePCB

```bash
# To convert to LibrePCB files, first have the files downloaded into downloads/
# Modify main.py with the LCSC ID of interest
and then run:
uv run main.py

=== Symbol Data Structure ===
Symbol shapes count: 43

=== Footprint Data Structure ===
Footprint shapes count: 131

=== Parsing Symbol ===

--- Canonical Symbol (Parsed from EasyEDA) ---
Symbol: ESP32-C6_C5364646
  UUID: cfa9cf40-5f9f-40ab-bb08-2df4168a5f3e
  Prefix: U?
  Origin: Pt(400.000, 300.000)
  Dimensions: 15.00 x 28.00 mm
  Pins (41)
  Graphics (2)

=== Parsing Footprint ===
Warning: Unknown EasyEDA layer name 'Ratlines' (id: 9). Mapping to DOCUMENTATION.
Warning: Unknown EasyEDA layer name 'Multi-Layer' (id: 11). Mapping to DOCUMENTATION.
Warning: Unknown EasyEDA layer name '3DModel' (id: 19). Mapping to DOCUMENTATION.
Warning: Unknown EasyEDA layer name 'DRCError' (id: DRCError). Mapping to DOCUMENTATION.

--- Canonical Footprint (Parsed from EasyEDA) ---
Footprint: QFN-40_L5.0-W5.0-P0.40-TL-EP3.3
  UUID: b0d5a736-74be-41d6-a029-8cc741e4302b
  Keywords: Microcontrollers (MCU/MPU/SOC)
  Pads (41)
  Graphics (90)

=== Serializing Footprint to LibrePCB ===
Footprint 'QFN-40_L5.0-W5.0-P0.40-TL-EP3.3' serialized to LibrePCB package: /Users/fred/LibrePCB-Workspace/data/libraries/local/EasyEDA.lplib/pkg/b0d5a736-74be-41d6-a029-8cc741e4302b/package.lp

=== Serializing Symbol to LibrePCB ===
  Consolidating duplicate pin: VDDA3P3
Symbol 'ESP32-C6_C5364646' serialized to LibrePCB symbol: /Users/fred/LibrePCB-Workspace/data/libraries/local/EasyEDA.lplib/sym/cfa9cf40-5f9f-40ab-bb08-2df4168a5f3e/symbol.lp
  - 40 unique pins (removed 1 duplicates)
  - Arranged pins on 2.54mm grid
  - Symbol dimensions (body): 15.00 x 28.00 mm

=== Serializing Component to LibrePCB ===
Component 'ESP32-C6_C5364646' serialized to LibrePCB component: /Users/fred/LibrePCB-Workspace/data/libraries/local/EasyEDA.lplib/cmp/d4e5e068-ea28-45c7-925d-4b6dbabfa970/component.lp

=== Serializing Device to LibrePCB ===
         - WARNING! Pad 2 without corresponding Pin (removed duplicate)
Device 'ESP32-C6_C5364646' serialized to LibrePCB component: /Users/fred/LibrePCB-Workspace/data/libraries/local/EasyEDA.lplib/dev/a32088c9-ef07-4d14-89e4-ef39c5bac4f3/device.lp

```

## Trying out the User Interface

Use `uv run main_ui.py` to test out the search interface, with EasyEDA parts search and footprint image / hero image review

## Tests

Use `uv run pytest` to run the unit tests
