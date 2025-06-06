# Global imports
from enum import Enum
from typing import List, Optional, Union

from pydantic import BaseModel, Field

# Local imports
from .layer import Layer


class TextAlignHorizontal(str, Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class TextAlignVertical(str, Enum):
    TOP = "top"
    MIDDLE = "middle"
    BOTTOM = "bottom"


# --- Geometric Primitives ---


class Point(BaseModel):
    x: float = Field(..., description="X in mm")
    y: float = Field(..., description="Y in mm")

    def __repr__(self) -> str:
        return f"Pt({self.x:.3f}, {self.y:.3f})"


class Point3D(BaseModel):
    x: float = Field(..., description="X in mm")
    y: float = Field(..., description="Y in mm")
    z: float = Field(..., description="Z in mm")


class EulerRotation(BaseModel):
    x: float = Field(0.0, description="Rotate X°")
    y: float = Field(0.0, description="Rotate Y°")
    z: float = Field(0.0, description="Rotate Z°")


# --- Graphic Primitives ---


class GraphicItem(BaseModel):
    layer: Layer


class Line(GraphicItem):
    start: Point
    end: Point
    width: float


class Polyline(GraphicItem):
    """Polyline for symbol graphics."""

    points: List[Point]
    stroke_width: float = 0.0  # 0 = hairline


class Arc(GraphicItem):
    center: Point
    radius: float
    start_angle: float
    end_angle: float
    width: float


class Ellipse(GraphicItem):
    """Ellipse shape."""

    center: Point
    radius_x: float
    radius_y: float
    stroke_width: float = 0.0
    filled: bool = False
    rotation: float = 0.0


class Circle(GraphicItem):
    center: Point
    radius: float
    stroke_width: float
    filled: bool = False


class Rectangle(GraphicItem):
    position: Point
    width: float
    height: float
    rotation: float = 0.0
    stroke_width: float
    filled: bool = False
    corner_radius: Optional[float] = None


class Polygon(GraphicItem):
    vertices: List[Point]
    stroke_width: float = 0.0
    filled: bool = True

    def __repr__(self):
        return f"Polygon {len(self.vertices)} {self.layer}"


class Text(GraphicItem):
    text: str
    text_type: Optional[str] = None  # 'name', 'value', 'prefix', etc.
    position: Point
    font_height: float
    stroke_width: float
    rotation: float = 0.0
    mirrored: bool = False
    visible: bool = True
    horizontal_align: TextAlignHorizontal = TextAlignHorizontal.LEFT
    vertical_align: TextAlignVertical = TextAlignVertical.BOTTOM

    def __repr__(self) -> str:
        return f"Text('{self.text}', pos={self.position}, h={self.font_height:.2f}, layer='{str(self.layer)}')"


GraphicElement = Union[Line, Polyline, Arc, Circle, Rectangle, Polygon, Text]
