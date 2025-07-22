# WebParts for LibrePCB

A component search and library management tool for LibrePCB. WebParts helps you find datasheets, footprints, and symbols from online vendors, then guides you through a review process to import them cleanly into your local LibrePCB libraries.

# Project Goals

The primary goal of this project is to solve a common challenge for LibrePCB users: the difficulty of finding and importing reliable component data. By providing a streamlined workflow to search, review, and manage library parts, WebParts aims to make the process of building a personal or team library significantly easier.

In LibrePCB's forums and in GitHub issues, the opinion seems to be that there's no easy, automatic way to get a reliable online parts catalog.
Library conversion is hard, and professional PCB designers already usually have to review online-sourced footprints. Compounding the issue is that different EDAs and PCB design softwares follow different conventions for how they label things in a schematic.

- **Simplify Part Discovery:** Serve as a companion to LibrePCB to make finding parts easier, searching across multiple online vendors.
- **Bridge the Gap:** Convert schematic symbols, footprints, and 3D models from various vendor formats into the native LibrePCB format.
- **Ensure Quality:** Provide a dedicated review workflow to validate and approve new library elements before they are committed, inspired by professional PCB design practices.

# Vision: The Library and Search Workflow

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

WebParts is designed around two core concepts: **Search** and the **Library**.

- **Search:** This is the discovery phase. You can search for components across supported online vendors. The Search page provides a rich interface to view component details, including datasheets, hero images, and rendered images of the symbol and footprint. This is where you decide if a part is a good candidate for your library.

- **Library:** This is your curated collection of components. When you find a part you want to use, you add it to your Library. Parts in the library have a lifecycle and a state of review. The application will help you track which components have been fully reviewed and approved.

The main user workflow is as follows:

1.  **Start in the Library:** The application opens to your Library page, showing your collection of components and their review status (e.g., "Footprint Review Needed", "Approved").
2.  **Find New Parts:** From the Library, you navigate to the Search page to find new components.
3.  **Add to Library:** Once you've found a suitable component in the search results, you click "Add to Library". This action brings the component into your local collection and starts the review process.
4.  **Review the Library Element:** Adding a new part takes you to the multi-step Library Element review page. Here, you'll be guided through:
    - **Footprint Review:** Compare the generated footprint against the datasheet. Use the image of the EasyEDA footprint (Not yet possible) alongside the exported PNG image of the current LibrePCB footprint for a quick check.
      - Display the list of pads, their signal names, and a hyperlink to the datasheet
      - Displays any already flagged error messages from librepcb-cli
      - If the user is happy with the footprint, they Approve it, and the app reports an approval to the central REST server to help with tracking of converted part approval
    - **Symbol Review:** Validate the schematic symbol.
    - **Assembly:** Map symbol pins to footprint pads.
    - **Finalize:** Commit the approved component to your LibrePCB library file.

This separation ensures that your primary library remains a clean, trusted source of components, while the search functionality provides a way to discover and import new parts.

# Usage

This will search for and download the EasyEDA data, convert it to the canonical data model, and serialize it into the `.lp` format required by LibrePCB. The output is placed in the LibrePCB library noted in constants.py

It is recommended to have [`uv`](https://docs.astral.sh/uv/) installed for managing Python environments and running scripts.

```bash
# To convert to LibrePCB files run cli.py with the LCSC ID of interest
uv run cli.py C2040
CLI - INFO - Starting process for LCSC ID: C2040
CLI - INFO - Searching for 'C2040'...
search - INFO - Delegating search for 'C2040' to LCSC engine...
CLI - INFO - Found exact match: RP2040
CLI - INFO - Fetching detailed CAD data...
adapters.easyeda.easyeda_api - INFO - Found cached 3D Model STEP file
library_manager - INFO - Created library directories for part 0e6097e2-8bd2-4994-b311-687c2df1ea80
library_manager - INFO -   OK.
library_manager - INFO - Saving footprint source JSON...
library_manager - INFO -   OK.
library_manager - INFO - Saving symbol source JSON...
library_manager - INFO -   OK.
workers.footprint_converter - INFO -
--- Starting Package Generation ---
2025-07-22 11:08:45,001 - workers.footprint_converter - INFO - Successfully serialized footprint to WebParts.lplib/pkg/39e1b05b-30bd-4c64-a6c9-a1b67d9eb207/package.lp
2025-07-22 11:08:45,001 - workers.footprint_converter - INFO - --- Package Generation Succeeded ---
Check 'WebParts.lplib/pkg/39e1b05b-30bd-4c64-a6c9-a1b67d9eb207' for non-approved messages...
  Approved messages: 0
  Non-approved messages: 10
workers.footprint_converter - INFO - Updated footprint manifest with 10 validation issues.
svg_utils - INFO - Overlaid 2 alignment crosshairs on WebParts.lplib/pkg/39e1b05b-30bd-4c64-a6c9-a1b67d9eb207/footprint.png
library_manager - INFO - --- Starting Symbol Generation ---
workers.symbol_converter - INFO - Parsing EasyEDA symbol data...
workers.symbol_converter - INFO - Consolidating duplicate pins for LibrePCB symbol file...
workers.symbol_converter - INFO -   Consolidating duplicate pin: IOVDD
workers.symbol_converter - INFO -   Consolidating duplicate pin: DVDD
library_manager - INFO - --- Symbol Generation Succeeded, now rendering and checking ---
workers.element_renderer - INFO - CLI Output:
Check 'WebParts.lplib/sym/c2754a5d-ac40-4cb1-b757-213b56759c67' for non-approved messages...
  Approved messages: 0
  Non-approved messages: 1
workers.element_renderer - INFO - Converting WebParts.lplib/sym/c2754a5d-ac40-4cb1-b757-213b56759c67/rendered.svg to WebParts.lplib/sym/c2754a5d-ac40-4cb1-b757-213b56759c67/rendered.png...
library_manager - INFO - Updated manifest for symbol c2754a5d-ac40-4cb1-b757-213b56759c67 with 1 issues and status approved.
library_manager - INFO - --- Starting Component Generation ---
workers.component_converter - INFO - --- Starting Component Generation ---
workers.component_converter - INFO - Component UUID: bf949642-8df0-4e94-85aa-3fab19059dfd
workers.component_converter - INFO - Successfully generated component 'RP2040'.
library_manager - INFO - --- Starting Device Generation ---
workers.device_converter - INFO - --- Starting Device Generation ---
workers.device_converter - INFO - Successfully generated device 'RP2040'.
library_manager - INFO - ✅ Successfully added 'RP2040' to library.
CLI - INFO - ✅ Process completed successfully!

```

## Trying out the User Interface

Use `uv run main_ui.py` to test out the search interface, with EasyEDA parts search and footprint image / hero image review

## Tests

Use `uv run pytest` to run the unit tests

# Future

An extension of this could be a "confidence score" for community-approved parts. After a user reviews and approves a footprint or symbol, this approval could be sent to a central server, helping to build a repository of trusted, community-vetted components.

See also [IDEAS.md](IDEAS.md) for more.
