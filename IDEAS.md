# Future Ideas and Enhancements

This document tracks ideas for future development, ranging from simple improvements to more complex architectural changes.

## Library Management

- **Persistent Library Storage:** Implement a robust way to save and load the user's library, likely using a simple database file (e.g., SQLite) or a structured JSON file.
- **Library View:** Design and build the main Library page UI. This should include:
  - A searchable, sortable list of all components in the library.
  - Clear status indicators for each component (e.g., "Needs Footprint Review", "Needs Symbol Review", "Approved").
  - The ability to filter the library by review status, component type, etc.
- **Component Deletion:** Add the ability to remove a component from the library.
- **Git Sync (Long Term):** Consider an optional Git integration to sync a user's library across multiple devices.

## Review Workflow Enhancements

- **Side-by-Side Datasheet Viewer:** Instead of just a link, embed a PDF viewer directly within the review pages to show the component datasheet next to the footprint or symbol being reviewed.
- **Deep Linking to LibrePCB Editor:** Investigate a way to create a button that deep-links directly to the specific library element in the user's running LibrePCB instance, making it easier to make manual corrections. Optional: Put background images on cache path for footprint review as implemented in https://github.com/LibrePCB/LibrePCB/pull/1450
- **Checklist-Based Review:** For the footprint and symbol review steps, provide a pre-defined checklist of common things to verify (e.g., "Pin 1 orientation correct", "Pad dimensions match datasheet", "Symbol outline conforms to standard").

## Core Conversion Engine

- **Migrate to Official Entities:** The current data models for footprints and symbols were built from scratch. The `librepcb-parts-generator` project has its own set of `entities`. We should migrate our conversion logic to use these official entities to improve compatibility and reduce maintenance.
- **Improved Solder Mask/Paste Handling:** The current conversion for footprints excludes custom solder mask polygons from EasyEDA. A more advanced approach would be to analyze these polygons and translate them into corresponding modifications on the solder mask and paste layers in LibrePCB.
- **Better Handling of Grid and Staggered Pins:** The conversion from EasyEDA's "half-grid" for staggered pins in symbols can be improved to produce cleaner, more consistently aligned symbols in LibrePCB.

## Community and Collaboration

- **Confidence Score System:** Implement the "approved parts" idea. When a user approves a component, this information could be sent to a central server. The server could then provide a "confidence score" for each part, indicating how many other users have successfully vetted it.
- **Shared Libraries:** Allow users to export their library and share it with other WebParts users.
- **Integration with LibrePCB Parts Service:** Explore the possibility of contributing approved, high-quality components back to the official LibrePCB parts service.
