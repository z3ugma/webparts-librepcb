# models/symbol.py
# Global imports
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union
from uuid import UUID as UUID

from pydantic import BaseModel, Field

# Local imports
from .graphics import GraphicElement, Point

# --- Enumerations ---


class ElectricalType(str, Enum):
    """Electrical types for pins."""

    UNDEFINED = "undefined"
    INPUT = "input"
    OUTPUT = "output"
    IO = "io"  # Input/Output
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
    """Schematic symbol pin."""

    uuid: UUID
    name: str = Field(..., description="Pin name (e.g., 'VCC', 'GND', 'GPIO1')")
    number: str = Field(..., description="Pin number (e.g., '1', '2', 'A1')")
    position: Point = Field(..., description="Pin position on symbol")
    direction: PinDirection = PinDirection.RIGHT
    length: Union[PinLength, float] = (
        PinLength.MEDIUM
    )  # Can be standard or custom length

    # Electrical properties
    electrical_type: ElectricalType = ElectricalType.PASSIVE

    # Display properties
    name_visible: bool = True
    number_visible: bool = True
    name_position: Optional[Point] = None  # Relative to pin base
    number_position: Optional[Point] = None  # Relative to pin base

    # Special pin decorations
    inverted: bool = False  # Circle at pin base (logical NOT)
    clock: bool = False  # Triangle at pin base (clock input)

    # SPICE properties
    spice_number: Optional[str] = None  # For SPICE simulation

    def __repr__(self) -> str:
        return (
            f"Pin({self.number}='{self.name}', {self.position}, {self.direction.value})"
        )


# --- Symbol Model ---


class Symbol(BaseModel):
    """Schematic symbol representation."""

    # Core Identification
    name: str = Field(..., description="Symbol name")
    uuid: Optional[UUID] = None

    # Symbol properties
    pins: List[Pin] = Field(default_factory=list)
    graphics: List[GraphicElement] = Field(default_factory=list)

    # Bounding box
    origin: Point = Field(default_factory=lambda: Point(x=0, y=0))
    width: float = 0.0
    height: float = 0.0

    # Component properties
    prefix: str = "U?"  # Default component prefix (U1, U2, etc.)
    default_value: Optional[str] = None  # Default component value

    # Package association
    package_name: Optional[str] = None  # Associated footprint package

    # SPICE properties
    spice_prefix: Optional[str] = None  # X for subcircuit, R for resistor, etc.
    spice_model: Optional[str] = None  # SPICE model name

    # Display properties
    name_visible: bool = True
    value_visible: bool = True
    prefix_visible: bool = True
    name_position: Optional[Point] = None
    value_position: Optional[Point] = None

    # Metadata
    description: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    author: Optional[str] = None
    version_str: Optional[str] = None
    created_at: Optional[datetime] = None
    generated_by: Optional[str] = None

    # Custom attributes for EDA-specific data
    custom_attributes: Dict[str, str] = Field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"<Symbol '{self.name}' / {len(self.pins)} pins / "
            f"{len(self.graphics)} graphics / uuid='{self.uuid}'>"
        )

    def pretty_print(self, indent_level: int = 0) -> None:
        """Pretty print the symbol."""
        prefix = "  " * indent_level
        print(f"{prefix}Symbol: {self.name}")
        if self.uuid:
            print(f"{prefix}  UUID: {self.uuid}")
        if self.description:
            print(f"{prefix}  Description: {self.description}")
        if self.package_name:
            print(f"{prefix}  Package: {self.package_name}")

        print(f"{prefix}  Prefix: {self.prefix}")
        if self.default_value:
            print(f"{prefix}  Default Value: {self.default_value}")

        print(f"{prefix}  Origin: {self.origin!r}")
        print(f"{prefix}  Dimensions: {self.width:.2f} x {self.height:.2f} mm")

        if self.pins:
            print(f"{prefix}  Pins ({len(self.pins)}):")
            for i, pin in enumerate(self.pins):
                print(f"{prefix}    [{i + 1}]: {pin!r}")

        if self.graphics:
            print(f"{prefix}  Graphics ({len(self.graphics)}):")
            for i, graphic in enumerate(self.graphics):
                print(
                    f"{prefix}    [{i + 1}]: {type(graphic).__name__} on {graphic.layer}"
                )

        if self.custom_attributes:
            print(f"{prefix}  Custom Attributes:")
            for k, v in self.custom_attributes.items():
                print(f"{prefix}    {k}: {v}")

    class Config:
        validate_assignment = True
        arbitrary_types_allowed = True
