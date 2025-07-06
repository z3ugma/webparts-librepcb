from enum import Enum
from typing import Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from constants import DEFAULT_VERSION

from .elements import BaseElement
from .graphics import GraphicElement, Point


class ElectricalType(str, Enum):
    UNDEFINED = "undefined"
    INPUT = "input"
    OUTPUT = "output"
    IO = "io"
    POWER = "power"
    PASSIVE = "passive"
    OPEN_COLLECTOR = "open_collector"
    OPEN_EMITTER = "open_emitter"
    TRISTATE = "tristate"
    UNSPECIFIED = "unspecified"


class PinDirection(str, Enum):
    """Physical direction of pin on symbol."""

    RIGHT = "right"  # Pin points right (0°)
    DOWN = "down"  # Pin points down (90°)
    LEFT = "left"  # Pin points left (180°)
    UP = "up"  # Pin points up (270°)


class PinLength(str, Enum):
    """Standard pin lengths."""

    SHORT = "short"  # 2.54mm
    MEDIUM = "medium"  # 5.08mm
    LONG = "long"  # 7.62mm


# --- Pin Model ---


class Pin(BaseModel):
    uuid: UUID
    name: str = Field(..., description="Pin name (e.g., 'VCC', 'GND', 'GPIO1')")
    number: str = Field(..., description="Pin number (e.g., '1', '2', 'A1')")
    position: Point
    direction: PinDirection = PinDirection.RIGHT
    length: Union[PinLength, float] = PinLength.MEDIUM
    electrical_type: ElectricalType = ElectricalType.PASSIVE
    name_visible: bool = True
    number_visible: bool = True
    name_position: Optional[Point] = None
    number_position: Optional[Point] = None
    inverted: bool = False
    clock: bool = False
    spice_number: Optional[str] = None


class Symbol(BaseElement):
    pins: List[Pin] = Field(default_factory=list)
    graphics: List[GraphicElement] = Field(default_factory=list)
    origin: Point = Field(default_factory=lambda: Point(x=0, y=0))
    width: float = 0.0
    height: float = 0.0
    prefix: str = ("U",)
    default_value: Optional[str] = None
    package_name: Optional[str] = None
    spice_prefix: Optional[str] = None
    spice_model: Optional[str] = None
    name_visible: bool = True
    value_visible: bool = True
    prefix_visible: bool = True
    name_position: Optional[Point] = None
    value_position: Optional[Point] = None
    version_str: str = DEFAULT_VERSION
    #     A version string consists of numbers separated by dots (e.g., 0.1 or 2024.06.21).
    # Each number segment must be an unsigned integer between 0 and 99,999.
    # There can be no more than 10 number segments in total.
    # Empty segments (like in 1..2) are not allowed.
    custom_attributes: Dict[str, str] = Field(default_factory=dict)

    class Config:
        validate_assignment = True
