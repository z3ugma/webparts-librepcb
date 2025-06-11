# WebParts Library Management System - Product Requirements & Future Ideas

## Vision & Current Implementation

WebParts acts as a management tool for standard LibrePCB libraries (.lplib). The system bridges the gap between component search/discovery and local library management by providing a structured workflow for importing, reviewing, and organizing electronic components from vendor databases into LibrePCB-compatible libraries.

### Core Architectural Principles

**Native Compatibility**: The managed library is a valid .lplib directory that can be used directly by LibrePCB without any conversion or special handling.

**Metadata Isolation**: WebParts-specific metadata is stored in a `webparts/` subdirectory and in `.wp` sidecar files, ensuring clean separation from LibrePCB's native data structures.

**Atomic Component Model**: The library is organized around atomic parts, where each part represents a complete electronic component with all its associated elements (footprint, symbol, component, device) linked through a central manifest.

**Vendor-Driven UUIDs**: All UUIDs for packages, symbols, components, and devices are sourced directly from the search provider (e.g., EasyEDA). This ensures stability across sessions and allows for reliable detection of existing parts when adding duplicates.

**Portable Library Structure**: All file references within manifests use UUID-based relative paths rather than absolute paths, ensuring the entire `.lplib` directory is fully portable and self-contained.

### Current Directory Structure

```
WebParts.lplib/
├── pkg/                           # LibrePCB packages (footprints)
│   └── {package_uuid}/
│       ├── package.lp             # LibrePCB package definition
│       ├── footprint.png          # Footprint visualization
│       ├── footprint.svg          # Footprint source
│       ├── source.json            # Original vendor data
│       └── {package_uuid}.footprint.wp  # WebParts metadata
├── sym/                           # LibrePCB symbols (future)
├── cmp/                           # LibrePCB components (future)
├── dev/                           # LibrePCB devices (future)
└── webparts/                      # WebParts management data
    ├── {device_uuid}.part.wp      # Central part manifests
    └── library.wp                 # Library-wide metadata
```

### Implemented Manifest System

**Central Part Manifest** (`{device_uuid}.part.wp`):

```json
{
  "version": 1,
  "lcsc_part": "C51888",
  "mpn": "DS2411P+",
  "manufacturer": "Analog Devices",
  "added_at_utc": "2025-06-10T22:00:00Z",
  "overall_status": "needs_review",
  "uuids": {
    "device": "9a9cdefa-6ecb-43a8-b96c-8c36858f8a5e",
    "component": "a8f84724-e5a8-466e-9d1b-9155b4832777",
    "symbol": "827ec0ab-817f-4369-8481-03a7f5126e6b",
    "package": "35c7d6b1-0af3-4f27-be24-ebc957e217b4"
  }
}
```

**Element-Specific Manifests** (`{uuid}.{type}.wp`):

```json
{
  "version": 1,
  "status": "needs_review",
  "validation": {
    "errors": [
      {
        "code": "INVALID_PAD_SHAPE",
        "message": "Pad '6' has an invalid shape.",
        "status": "unresolved"
      }
    ],
    "warnings": [
      {
        "code": "SILKSCREEN_OUTSIDE_BOUNDS",
        "message": "Silkscreen is outside the component boundary.",
        "status": "unresolved"
      }
    ]
  }
}
```

### Current Data Architecture

**Shared Data Models** (`models/common_info.py`): Common information models eliminate duplication between search results and library parts:

- `ImageInfo`: Metadata about component images
- `FootprintInfo`: Footprint specifications and metadata
- `SymbolInfo`: Symbol specifications and metadata
- `ComponentInfo`: Component-level information
- `DeviceInfo`: Device-level specifications

**Path Resolution**: File paths are never stored in manifests. The UI layer constructs paths at runtime using: `{library_base_path}/{element_type}/{uuid}/{filename}`

---

## Library Management Enhancements

### Immediate Priorities

- **Complete Library View Implementation**: Build the main Library page UI with:

  - Searchable, sortable list of all components based on central manifests
  - Clear status indicators for each component ("Needs Footprint Review", "Needs Symbol Review", "Approved")
  - Filtering by review status, component type, manufacturer, date added
  - Bulk operations (approve multiple components, batch status updates)

  **Library View:** Design and build the main Library page UI. This should include:

  - A searchable, sortable list of all components in the library.
  - Clear status indicators for each component (e.g., "Needs Footprint Review", "Needs Symbol Review", "Approved").
  - The ability to filter the library by review status, component type, etc.

- **Component Deletion:** Add the ability to remove a component from the library.
- **Git Sync (Long Term):** Consider an optional Git integration to sync a user's library across multiple devices.

- **Component Deletion & Management**:

  - Add ability to remove components from library (clean up manifests and assets)
  - Implement component archiving (soft delete) vs permanent removal
  - Handle orphaned assets and manifest cleanup

- **Enhanced Validation System**:
  - Expand validation rules beyond basic structural checks
  - Add configurable validation severity levels
  - Implement validation rule versioning for backward compatibility
  - Allow custom validation rules per component type

## Review Workflow Enhancements

### Immediate UI Improvements

- **Side-by-Side Datasheet Viewer**: Embed PDF viewer directly within review pages to show component datasheet next to footprint/symbol being reviewed

- **Checklist-Based Review**: Provide pre-defined, customizable checklists for common verification tasks:

  - Footprint: "Pin 1 orientation correct", "Pad dimensions match datasheet", "Courtyard appropriate"
  - Symbol: "Pin arrangement logical", "Power pins positioned correctly", "Symbol outline conforms to standard"

- **Review History & Notes**:
  - Track review decisions and reasoning
  - Allow reviewers to add notes for future reference
  - Show who reviewed what and when (for collaborative workflows)

### Advanced Review Features

- **Deep Linking to LibrePCB Editor**: Create buttons that deep-link directly to specific library elements in running LibrePCB instance for manual corrections

- **Background Image Integration**: Implement datasheet page overlays for footprint review (similar to LibrePCB PR #1450)

- **Review Templates**:
  - Save and reuse review configurations for similar component families
  - Import/export review checklists and validation rules
  - Component-type-specific review workflows

## Core Conversion Engine Improvements

### Architecture Modernization

- **Migrate to Official LibrePCB Entities**: Replace custom data models with official entities from `librepcb-parts-generator` project for better compatibility and reduced maintenance

- **Enhanced EasyEDA Parsing**:

  - Improved solder mask/paste handling - analyze custom polygons and translate to LibrePCB modifications
  - Better grid handling for staggered pins in symbols
  - Support for more EasyEDA element types (arcs, complex polygons, text styling)

- **Multi-Vendor Support Architecture**:
  - Pluggable converter system for different vendor formats
  - Normalized intermediate representation for all vendors
  - Vendor-specific quirks and workarounds isolation

### Quality & Accuracy Improvements

- **Advanced Symbol Generation**:

  - Intelligent pin arrangement based on component type
  - Automatic power/ground pin grouping / Net assignment
  - Standard symbol outline generation based on pin count

- **Footprint Enhancement**:

  - 3D model
  - Advanced pad shape support (rounded rectangles, custom shapes)
  - Thermal relief handling?

- **Validation Engine**:
  - Cross-reference validation between symbol pins and footprint pads

## Community and Collaboration Features

- **Confidence Score System:** Implement the "approved parts" idea. When a user approves a component, this information could be sent to a central server. The server could then provide a "confidence score" for each part, indicating how many other users have successfully vetted it.
- **Shared Libraries:** Allow users to export their library and share it with other WebParts users.

- **Confidence Score Implementation**:

  - Track user approvals for each component
  - Generate confidence scores based on community validation
  - Highlight high-confidence components in search results
  - Flag potentially problematic components based on rejection patterns

### Sharing and Distribution

- **Integration with LibrePCB Ecosystem**:

  - Contribute approved components back to official LibrePCB parts service
  - Sync with official part updates and corrections
  - Two-way communication for part quality feedback

  - **Integration with LibrePCB Parts Service:** Explore the possibility of contributing approved, high-quality components back to the official LibrePCB parts service.

### Data and Analytics

- **Usage Analytics**:

  - Track most-used components and manufacturers
  - Identify gaps in library coverage
  - Component popularity trends and recommendations

- **Quality Metrics**:
  - Validation error rates by vendor and component type
  - Review time tracking and efficiency metrics
  - Community feedback aggregation and trending

## Technical Infrastructure Enhancements

### Deployment and Distribution

- **Packaging Improvements**:

  - Native installers for major platforms
  - Auto-update mechanism for application and validation rules

---

## Implementation Priorities

**Phase 1 (Current)**: Complete core library management with search integration
**Phase 2**: Enhanced review workflows and validation system
**Phase 3**: Community features and multi-vendor support  
**Phase 4**: Advanced collaboration and enterprise features
