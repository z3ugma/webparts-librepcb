from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from constants import DEFAULT_VERSION

from .elements import BaseElement
from .graphics import EulerRotation, GraphicElement, Point, Point3D
from .layer import LayerRef


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
    layer: LayerRef
    drill_shape: Optional[DrillShape] = None
    drill_diameter: Optional[float] = None
    drill_slot_length: Optional[float] = None
    plated: Optional[bool] = True
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


class Drill(BaseModel):
    position: Point
    shape: DrillShape = DrillShape.ROUND
    diameter: float
    slot_length: Optional[float] = None
    plated: bool = False
    layer: LayerRef

    @model_validator(mode="after")
    def _validate(cls, m):
        if m.shape == DrillShape.OBLONG and m.slot_length is None:
            raise ValueError("slot_length required for OBLONG")
        if m.shape == DrillShape.ROUND and m.slot_length is not None:
            raise ValueError("slot_length not allowed for ROUND")
        return m


class Model3D(BaseModel):
    uuid: Optional[UUID] = None
    offset: Point3D = Field(default_factory=lambda: Point3D(x=0, y=0, z=0))
    rotation: EulerRotation = Field(default_factory=lambda: EulerRotation())
    scale: Point3D = Field(default_factory=lambda: Point3D(x=1, y=1, z=1))


class Footprint(BaseElement):
    pads: List[Pad] = Field(default_factory=list)
    graphics: List[GraphicElement] = Field(default_factory=list)
    origin: Point = Field(default_factory=lambda: Point(x=0, y=0))
    height: float = 0
    width: float = 0
    version_str: str = DEFAULT_VERSION
    #     A version string consists of numbers separated by dots (e.g., 0.1 or 2024.06.21).
    # Each number segment must be an unsigned integer between 0 and 99,999.
    # There can be no more than 10 number segments in total.
    # Empty segments (like in 1..2) are not allowed.
    model_3d: Optional[Model3D] = None
    custom_attributes: Dict[str, str] = Field(default_factory=dict)

    class Config:
        validate_assignment = True
