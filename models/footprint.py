# footprint.py
# Global imports
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

# Local imports
from .graphics import EulerRotation, GraphicElement, Point, Point3D
from .layer import Layer

# --- Enumerations ---


class AssemblyType(str, Enum):
    NONE = None  # Nothing to mount (i.e. not a package, just a footprint)
    THT = "tht"  # Pure THT package
    SMT = "smt"  # Pure SMT package
    MIXED = "mixed"  # Mixed THT/SMT package
    OTHER = "other"  # Anything special, e.g. mechanical parts
    AUTO = "auto"  # Auto detection (deprecated, only for file format migration!)


class PadShape(str, Enum):
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    OVAL = "oval"
    POLYGON = "polygon"
    ROUNDRECT = "roundrect"


class PadType(str, Enum):
    SMD = "smd"
    THROUGH_HOLE = "through_hole"
    VIA = "via"
    CONNECT = "connect"
    MECHANICAL = "mechanical"


class DrillShape(str, Enum):
    ROUND = "round"
    OBLONG = "oblong"


# --- Pads and Drills ---


class Pad(BaseModel):
    number: str
    uuid: UUID
    pad_type: PadType = PadType.SMD
    shape: PadShape
    position: Point
    width: float
    height: Optional[float] = None
    rotation: float = 0.0
    layer: Layer

    drill_shape: Optional[DrillShape] = None
    drill_diameter: Optional[float] = None
    drill_slot_length: Optional[float] = None
    plated: Optional[bool] = True

    start_layer: Optional[Layer] = None
    end_layer: Optional[Layer] = None

    solder_mask_margin: Optional[float] = None
    paste_mask_margin: Optional[float] = None

    corner_radius_ratio: Optional[float] = None
    vertices: Optional[List[Point]] = None

    attributes: Dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_shape(cls, m):
        if (
            m.shape in {PadShape.RECTANGLE, PadShape.OVAL, PadShape.ROUNDRECT}
            and m.height is None
        ):
            raise ValueError("Height required for non-circular pads")
        if m.shape == PadShape.POLYGON and not m.vertices:
            raise ValueError("Vertices required for POLYGON")
        if m.shape == PadShape.ROUNDRECT and m.corner_radius_ratio is None:
            m.corner_radius_ratio = 0.1
        return m

    @model_validator(mode="after")
    def _validate_drill(cls, m):
        tht = m.pad_type in {PadType.THROUGH_HOLE, PadType.VIA}
        if tht:
            if m.drill_diameter is None:
                raise ValueError("drill_diameter required for THT/Via")
            if m.drill_shape is None:
                m.drill_shape = DrillShape.ROUND
            if m.drill_shape == DrillShape.OBLONG and m.drill_slot_length is None:
                raise ValueError("drill_slot_length required for OBLONG")
        else:
            if any([m.drill_diameter, m.drill_shape, m.drill_slot_length]):
                raise ValueError("Drill properties only allowed on THT/Via")
        return m

    def __repr__(self) -> str:
        return f"Pad {self.number} {self.shape.value[0:4]} {self.pad_type.value}" + (
            f", drill={self.drill_diameter:.3f}" if self.drill_diameter else ""
        )


class Drill(BaseModel):
    position: Point
    shape: DrillShape = DrillShape.ROUND
    diameter: float
    slot_length: Optional[float] = None
    plated: bool = False
    layer: Layer

    @model_validator(mode="after")
    def _validate(cls, m):
        if m.shape == DrillShape.OBLONG and m.slot_length is None:
            raise ValueError("slot_length required for OBLONG")
        if m.shape == DrillShape.ROUND and m.slot_length is not None:
            raise ValueError("slot_length not allowed for ROUND")
        return m


# --- 3D Model ---


class Model3D(BaseModel):
    uuid: Optional[UUID] = None  # LibrePCB's main identifier
    offset: Point3D = Field(default_factory=lambda: Point3D(x=0, y=0, z=0))
    rotation: EulerRotation = Field(default_factory=lambda: EulerRotation())
    scale: Point3D = Field(default_factory=lambda: Point3D(x=1, y=1, z=1))


# --- Main Footprint ---


class Footprint(BaseModel):
    # Core Identification
    name: str  # Corresponds to LibrePCB's primary name (e.g., English)
    uuid: Optional[UUID] = None  # LibrePCB's main identifier

    # Descriptive Metadata
    description: Optional[str] = None  # Primary description
    keywords: List[str] = Field(
        default_factory=list
    )  # Was 'tags', 'keywords' is more aligned with LibrePCB
    # For LibrePCB categories, this would store names/paths,
    # or you might need a separate list of category UUIDs if strict mapping is desired.

    # Versioning and Authorship
    version_str: Optional[str] = (
        None  # e.g., "1.0.0", "20230315" (LibrePCB has a structured Version)
    )
    author: Optional[str] = None

    # Lifecycle & Provenance
    created_at: Optional[datetime] = None
    deprecated: bool = False
    generated_by: Optional[str] = None  # e.g., "ConverterTool v1.2", "LibrePCB 0.1.7"

    # Physical & Graphical Definition (existing fields are good)
    pads: List[Pad] = Field(default_factory=list)
    graphics: List[GraphicElement] = Field(default_factory=list)
    origin: Point = Field(default_factory=lambda: Point(x=0, y=0))
    height: float = 0
    width: float = 0
    model_3d: Optional[Model3D] = None

    # For other EDA-specific or custom passthrough data not covered above
    # or for localized strings if you choose not to model them directly yet.
    custom_attributes: Dict[str, str] = Field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"<Footprint {self.name}' / {self.width:.2f}mm * {self.height:.2f}mm / {len(self.pads)} pads / {len(self.graphics)} graphics /"
            f"uuid='{self.uuid}'>"
        )

    def __str__(self) -> str:
        # A more detailed pretty print than __repr__ for when print(footprint_obj) is called
        # Could be similar to pretty_print or simpler.
        # For now, let's make it slightly more informative than __repr__
        s = [f"Footprint: {self.name}"]
        if self.uuid:
            s.append(f"  UUID: {self.uuid}")
        if self.description:
            s.append(f"  Description: {self.description[:60]}...")
        s.append(f"  Pads: {len(self.pads)}")
        s.append(f"  Graphic Elements: {len(self.graphics)}")
        if self.model_3d:
            s.append(f"  3D Model: {self.model_3d.path}")
        return "\n".join(s)

    def pretty_print(self, indent_level: int = 0) -> None:
        """Custom pretty printer for the Footprint object."""
        prefix = "  " * indent_level
        print(f"{prefix}Footprint: {self.name}")
        if self.uuid:
            print(f"{prefix}  UUID: {self.uuid}")
        if self.version_str:
            print(f"{prefix}  Version: {self.version_str}")
        if self.author:
            print(f"{prefix}  Author: {self.author}")
        if self.description:
            print(f"{prefix}  Description: {self.description}")
        if self.keywords:
            print(f"{prefix}  Keywords: {', '.join(self.keywords)}")

        print(f"{prefix}  Origin: {self.origin!r}")

        if self.pads:
            print(f"{prefix}  Pads ({len(self.pads)}):")
            for i, pad in enumerate(self.pads):
                # You can choose to print the full repr or a custom summary
                print(f"{prefix}    [{i}]: {pad!r}")
        else:
            print(f"{prefix}  Pads: None")

        if self.graphics:
            print(f"{prefix}  Graphics ({len(self.graphics)}):")
            for i, graphic in enumerate(self.graphics):
                print(
                    f"{prefix}    [{i}]: {graphic!r}"
                )  # Relies on __repr__ of each graphic type
        else:
            print(f"{prefix}  Graphics: None")

        if self.model_3d:
            print(f"{prefix}  3D Model:")
            print(f"{prefix}    Path: {self.model_3d.uuid}")
            print(
                f"{prefix}    Offset: {self.model_3d.offset!r}"
            )  # Assuming Point3D has a good __repr__
            print(
                f"{prefix}    Rotation: {self.model_3d.rotation!r}"
            )  # Assuming EulerRotation has a good __repr__

        if self.custom_attributes:
            print(f"{prefix}  Custom Attributes:")
            for k, v in self.custom_attributes.items():
                print(f"{prefix}    {k}: {v}")

    class Config:
        validate_assignment = True
        arbitrary_types_allowed = True  # For datetime and UUID
