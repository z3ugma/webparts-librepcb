- Put background images on cache path for footprint review
  /Users/fred/Library/Caches/LibrePCB/LibrePCB/backgrounds/48d34c11-4c87-4378-a402-47d1ed5bc2e8/image.png
  lives in the cache dir of https://doc.qt.io/qt-6/qstandardpaths.html
  https://github.com/LibrePCB/LibrePCB/pull/1450

- Use https://librepcb.org/docs/cli/open-library/ and the SVG export to do side-by-side comparisons

- Migrate to the Entities in https://github.com/LibrePCB/librepcb-parts-generator/tree/master/entities?
  I'm realizing I have basically reinvented the wheel for my EasyEDA serializer and will probably switch to importing these instead

Hard things:

- Symbols in EasyEDA can have multiple pins with the same name/net designator like you see VDDA3P3 is pads 2 and 3. In LibrePCB this would be one signal/pin mapped to both pads
- Symbols in EasyEDA have a staggered "half grid" so you need to round up or down to get the pins to align on the symbol grid in LibrePCB
- Package footprints in EasyEDA have a dedicated solder mask polygon layer vs the inferred solder mask & paste in LibrePCB. I am excluding those polygons for now. I wonder if there will be times where there is manually some element on the mask/paste layer that will need to translate over better

√ EasyEDA.lplib % /Applications/LibrePCB.app/Contents/MacOS/librepcb-cli open-library --all -v --check .

# Review Workflow

1. Enter the LCSC element you want. WebParts downloads the JSON and SVGs for that element and shows those SVGs up on the screen for confirmation dialog
2. Confirm that's the element you wanted.
3. Proceed with conversion of symbol, footprint, and 3D model into library elements
4. Run the LibrePCB library element checker and grab the warning and error messages

## Footprint Package

Have 2 windows side-by-side: the LibrePCB library element footprint editor, and the WebParts step-by-step guide window

5. First, validate the footprint.

- Use the image of the EasyEDA footprint
  - (Not yet possible) alongside the exported PNG image of the current LibrePCB footprint for a quick check.
- Display the list of pads, their signal names, and a hyperlink to the datasheet
- Displays any already flagged error messages from librepcb-cli

6. If the user is happy with the footprint, they Approve it, and the app reports an approval to the central REST server to help with tracking of converted part approval

7. Else - (not yet possible) - User clicks URL that deeplinks you into the LibrePCB app and opens up the footprint library element for editing
8. Optional: Put background images on cache path for footprint review as implemented in https://github.com/LibrePCB/LibrePCB/pull/1450
9. Reviewer makes edits in LibrePCB and the checks re-run. Keep editing until satisfied.
10. In the WebParts tool, click "refresh" to run the CLI element checker and image export, then indicate Approval

## Symbol

Repeat steps 5-10 for the schematic Symbol instead of the footprint

## Component and Device

11. Proceed with the autogeneration of the Component and Device
12. Handle any duplicated signals or unconnected pads in the component and device.
